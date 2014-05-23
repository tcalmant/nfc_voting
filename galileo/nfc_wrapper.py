#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
NFC device wrapper

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Local
import constants

# nfcpy
import nfc.dev

# PyUSB (1.x)
import usb.core

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Instantiate, Validate, \
    Invalidate, Provides

# Standard library
import functools
import logging
import threading

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

def nfc_device_lookup():
    """
    Looks for usable NFC devices

    :return: A list of (bus, device) tuples for connected NFC devices
    """
    # Known devices vendor and product IDs
    usable_devs = set(nfc.dev.usb_device_map.keys())

    # USB lookup filter
    def nfc_match(dev):
        """
        Checks if the given device has known identifiers
        """
        return (dev.idVendor, dev.idProduct) in usable_devs

    # Return a tuple of 3 decimal digits strings
    out_str = '{0:03d}'
    return [(out_str.format(dev.bus), out_str.format(dev.address))
            for dev in usb.core.find(True, custom_match=nfc_match)]

# ------------------------------------------------------------------------------

class NFCDevice(object):
    """
    Wraps an NFC device
    """
    def __init__(self, busName, deviceName):
        """
        Sets up the device
        """
        # Compute device name
        self.__name = 'usb:{0}:{1}'.format(busName, deviceName)

        # Logger
        self.__logger = logging.getLogger("NFC-{0}".format(self.__name))

        # Prepare the device
        self.__logger.info("Preparing device %s", self.__name)
        self.nfc = nfc.ContactlessFrontend(self.__name)

        # Stop event
        self.__event = threading.Event()

        # Listening thread
        self.__thread = None

        # Callback
        self.on_tag = None


    def __str__(self):
        """
        String representation
        """
        return "NFCDevice at {0}".format(self.__name)


    def close(self):
        """
        Closes the device
        """
        # Stop the thread
        self.stop()

        # Close the frontend
        self.__event.set()
        self.nfc.close()
        self.nfc = None


    def __on_connect(self, tag):
        """
        A tag has been detected
        """
        if self.on_tag is not None:
            try:
                self.on_tag(tag)

            except Exception as ex:
                # Avoid exception to go up to NFCpy
                self.__logger.exception("Error handling tag: %s", ex)

        return True


    def __nfc_terminate(self):
        """
        Method to force the "connect" method of NFCpy to return
        """
        return self.__event.is_set()


    def listen(self):
        """
        Waits for tags in another thread
        """
        self.__thread = threading.Thread(name="NFCListen-{0}" \
                                         .format(self.__name),
                                         target=self.wait_for_tag,
                                         args=(True,))
        self.__thread.start()


    def stop(self):
        """
        Stops the listening thread
        """
        # Set the event
        self.__event.set()

        if self.__thread is not None and self.__thread.is_alive():
            # Wait for the thread to stop
            self.__thread.join()

        # Clear references
        self.__thread = None


    def wait_for_tag(self, loop=False):
        """
        Waits for a tag
        """
        # Clear the event
        self.__event.clear()

        # Blocking call
        if loop:
            # Loop until stop() is called
            while not self.__nfc_terminate():
                self.nfc.connect(rdwr={'on-connect': self.__on_connect},
                                 terminate=self.__nfc_terminate)

        else:
            # Single call
            self.nfc.connect(rdwr={'on-connect': self.__on_connect},
                                 terminate=self.__nfc_terminate)

# ------------------------------------------------------------------------------

class DataEvent(object):
    """
    An Event with some associated data
    """
    def __init__(self):
        """
        Sets up the event
        """
        self.__lock = threading.Lock()
        self.__event = threading.Event()
        self.__data = None

    def clear(self):
        """
        Clears the event
        """
        with self.__lock:
            self.__event.clear()
            self.__data = None

    def is_set(self):
        """
        Checks if the event is set
        """
        return self.__event.is_set()

    def get_data(self):
        """
        Returns the data associated to the event
        """
        return self.__data

    def set(self, data=None):
        """
        Sets the event. Updates data only if the event has not yet been set
        """
        with self.__lock:
            if not self.__event.is_set():
                self.__event.set()
                self.__data = data

    def wait(self, timeout=None):
        """
        Waits for the event

        :param timeout: Wait timeout (in seconds) or None
        """
        return self.__event.wait(timeout)

# ------------------------------------------------------------------------------

@ComponentFactory()
@Provides(constants.SERVICE_NFC)
@Instantiate('nfc-handler')
class NFCHandler(object):
    """
    Handles the NFC devices connected to the host
    """
    def __init__(self):
        """
        Sets up members
        """
        # Detected devices
        self._devices = []


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Look for devices
        self._devices = [NFCDevice(busName, devName)
                         for busName, devName in nfc_device_lookup()]


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Close all devices
        for device in self._devices:
            try:
                device.close()

            except Exception as ex:
                _logger.error("Error releasing a NFC device: %s", ex)


    def get_devices(self):
        """
        Looks for all USB NFC readers

        :return: The list of NFC USB devices
        """
        return self._devices[:]


    def wait_any_tag(self, devices=None):
        """
        Waits for a tag to be detected on any connected device

        :param devices: NFC devices to listen to
        """
        return self.__wait_tag(devices or self._devices)


    def __on_association_tag(self, event, device, tag):
        """
        Association tag handling (called by NFCpy)

        :param event: Association data event
        :param device: A (busId, deviceId) tuple
        :param tag: The detected tag
        """
        event.set(device)


    def __wait_tag(self, devices):
        """
        Returns the first device which receives a tag (used for association)

        :param devices: A list of VoteDevice objects
        :return: The first device which detected a tag
        """
        if not devices:
            return None

        elif len(devices) == 1:
            # Only one device available, avoid the test
            return devices[0]

        # Tag reception event
        event = DataEvent()

        for device in devices:
            # Prepare the front ends
            device.on_tag = functools.partial(self.__on_association_tag,
                                              event, device)
            device.listen()

        # Wait for a tag...
        event.wait()

        # Stop listening to tags
        for device in devices:
            device.stop()

        # Return the tagged device
        return event.get_data()
