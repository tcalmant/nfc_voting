#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
NFC vote machine

:authors: Antoine GERVAIL, Amine ZIAN­CHERIF, Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Configuration constants
import constants

# Paho MQTT client
import paho.mqtt.client as paho

# libusb Python binding
import usb

# NFCpy
import nfc

# Standard library
import functools
import logging
import threading
import time

# ------------------------------------------------------------------------------

def nfc_device_lookup(nfc_dev=(0x04E6, 0x5591)):
    """
    Looks for known NFC devices

    :param nfc_dev: A USB device identification tuple
                    (vendor, product)
    :return: A list of (bus, device) tuples for connected devices
    """
    matching = []

    # For each USB bus
    for bus in usb.busses():
        # For each device
        for dev in bus.devices:
            # Check if the device matches the USB identifier
            usb_ident = (dev.idVendor, dev.idProduct)
            if usb_ident == nfc_dev:
                matching.append((bus.dirname, dev.filename))

    return matching

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

class VoteLED(object):
    """
    Represents the LED(s) associated to a vote
    """
    def __init__(self):
        """
        Sets up the LED(s) wrapper
        """
        self.pins = {}

    def setup(self, values_pins):
        """
        Sets up the GPIO pins

        :param pins: LED GPIO pins associated to vote values: value -> pin(s).
                     "Pin(s)" can be a single value (valid LED) or a
                     2-items tuple (for (valid, invalid) LEDs)
        """
        for value, pins in values_pins.items():
            if isinstance(pins, (tuple, list)):
                # Copy the given values
                self.pins[value] = tuple(pins)
            else:
                # Ensure we have a tuple
                self.pins[value] = tuple(pins,)

            # TODO: setup GPIO

    def close(self):
        """
        Cleans up the GPIO pins
        """
        # TODO: tear down GPIO
        pass


    def _led_change(self, pin, state):
        """
        Lights up/down the LED at the given pin

        :param pin: LED pin
        :param state: If True, lights up, else lights down
        """
        # TODO: replace with GPIO
        if state:
            state_str = "UP"
        else:
            state_str = "DOWN"

        logging.debug("[[ pin %s %s ]]", pin, state_str)


    def valid(self, value, state):
        """
        Lights up or down the valid (green) LED

        :param value: Vote value
        :param state: If True, lights up, else lights down
        """
        try:
            pin = self.pins[value][0]
            if pin is None:
                raise IndexError()

        except (KeyError, IndexError):
            # Green LED is missing
            pass

        else:
            self._led_change(pin, state)


    def invalid(self, value, state):
        """
        Lights up or down the invalid (red) LED

        :param state: If True, lights up, else lights down
        """
        try:
            pin = self.pins[value][1]
            if pin is None:
                raise IndexError()

        except (KeyError, IndexError):
            # Red LED is missing
            pass

        else:
            self._led_change(pin, state)

# ------------------------------------------------------------------------------

class VoteDevice(object):
    """
    Wraps the NFC code
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

class VotingMachine(object):
    """
    Voting machine engine
    """
    def __init__(self, mqtt_topic='vote'):
        """
        Sets up members
        """
        # NFC front ends
        self.__nfc_devs = []

        # MQTT Client connection
        self.__mqtt = None

        # MQTT vote topic
        self.__mqtt_topic = mqtt_topic

        # LEDs handling
        self.__leds = VoteLED()


    def close(self):
        """
        Closes the MQTT connection and releases NFC devices
        """
        # Clean up NFC
        for clf in self.__nfc_devs:
            clf.close()
        del self.__nfc_devs[:]

        # Clean up MQTT
        self.__mqtt.disconnect()
        self.__mqtt = None

        # Clean up LEDs
        self.__leds.close()


    def connect_mqtt(self, host, port=1883):
        """
        Connects the MQTT client to the server

        :param host: MQTT server host
        :param port: MQTT server port
        """
        self.__mqtt = paho.Client()
        self.__mqtt.connect(host, port)


    def setup_leds(self, value_leds):
        """
        Sets up LEDs GPIO

        :param value_leds: Vote value -> LED GPIO pins
        """
        self.__leds.setup(value_leds)


    def associate_nfc(self, vote_values):
        """
        Associates a NFC device with a vote value. Lights up the associated LEDs

        :param vote_values: A list of possible vote values
        :raise ValueError: Not enough NFC devices
        """
        # Light down all LEDs
        for value in vote_values:
            self.__leds.valid(value, False)
            self.__leds.invalid(value, False)

        # Get all known devices
        found_devices = nfc_device_lookup()
        if len(found_devices) < len(vote_values):
            raise ValueError("Not enough NFC devices found")

        # Prepare them
        remaining_devices = [VoteDevice(busName, devName)
                             for busName, devName in found_devices]

        # Store them
        self.__nfc_devs = remaining_devices[:]

        # vote value -> VoteDevice
        value_device = {}

        for idx, value in enumerate(vote_values):
            if idx > 0:
                # Wait a bit so that the user removes the tag from the device
                time.sleep(.5)

            print('Associating value {0}...'.format(value))
            # Lights up LED
            print('... Lighting up LED')
            self.__leds.valid(value, False)
            self.__leds.invalid(value, True)

            # Associate a device
            print('... Waiting for association')
            device = self.__wait_tag(remaining_devices)
            value_device[value] = device

            # Remove the device from the list
            remaining_devices.remove(device)

            # Change LED state
            print('... Changing LED state')
            self.__leds.valid(value, True)
            self.__leds.invalid(value, False)

        # All done
        print('All values associated')

        # Prepare callbacks
        for value, device in value_device.items():
            # Prepare the NFC front end
            device.on_tag = functools.partial(self.__on_vote_tag, value)
            device.listen()


    def __on_vote_tag(self, value, tag):
        """
        Vote tag handling (called by NFCpy)

        :param value: Vote value
        :param tag: Detected tag
        """
        # Light up the LED
        self.__leds.valid(value, True)

        try:
            # Get vote ID
            id_vote = tag.ndef.message[0].data

            # Format the content
            payload = "{0} {1}".format(id_vote[-4:], value)

            # Publish the message
            print(">>> Publishing vote: {0}".format(payload))
            self.__mqtt.publish(self.__mqtt_topic, payload, qos=2)

            # Wait a bit
            state = True
            for _ in range(20):
                # ACK LED
                self.__leds.valid(value, state)
                time.sleep(.1)

            # Light down the LED
            self.__leds.valid(value, False)

        except Exception as ex:
            logging.exception("Error handling vote: %s", ex)

            # Light down green LED
            self.__leds.valid(value, False)

            # Warning LED
            state = True
            for _ in range(10):
                self.__leds.invalid(value, state)
                time.sleep(.1)
                state = not state

            # Light up red LED
            self.__leds.invalid(value, True)



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
        if len(devices) == 1:
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

# ------------------------------------------------------------------------------

def main(config):
    """
    Entry point

    :param config: A Configuration object
    """
    # Get vote values
    values = config.getlist(constants.SECTION_VOTE, constants.VOTE_VALUES,
                            constants.VOTE_VALUES_DEFAULT)
    if not values:
        print('No values given in configuration')
        return 1

    # Get LEDs configuration
    value_leds = {}
    for value in values:
        value_leds[value] = tuple(int(pin) for pin \
                    in config.getlist(constants.SECTION_LEDS, str(value), []))

    # Get MQTT configuration
    host = config.get(constants.SECTION_MQTT, constants.MQTT_HOST,
                          constants.MQTT_HOST_DEFAULT)
    port = config.getint(constants.SECTION_MQTT, constants.MQTT_PORT,
                         constants.MQTT_PORT_DEFAULT)
    topic = config.get(constants.SECTION_MQTT, constants.MQTT_TOPIC,
                       constants.MQTT_TOPIC_DEFAULT)

    # Prepare the vote machine
    vote = VotingMachine(topic)
    try:
        vote.connect_mqtt(host, port)

    except Exception as ex:
        print("Error connecting to the MQTT server: {0}".format(ex))
        return 2


    # Setup LEDs
    vote.setup_leds(value_leds)

    # Associate tags
    try:
        vote.associate_nfc(values)

    except ValueError as ex:
        # Error associating NFC devices
        print("Error associating NFC devices: {0}".format(ex))
        return 3

    # Prepare the event we wait to stop
    event = threading.Event()

    # Wait until the end of the vote (signal or KeyboardInterrupt)
    try:
        while not event.is_set():
            event.wait(.5)
    except KeyboardInterrupt:
        print('Keyboard interruption... stopping')

    # Clean up
    vote.close()
    return 0

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # Script entry point
    import sys

    # Setup logs
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("nfc").setLevel(logging.CRITICAL)

    # Read configuration
    config = constants.Configuration()

    # Run the vote machine
    sys.exit(main(config))
