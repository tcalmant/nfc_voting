#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
NFC vote machine

:authors: Antoine GERVAIL, Amine ZIAN­CHERIF, Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Local constants
import constants

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Instantiate, Validate, \
    Invalidate, Requires

# Standard library
import functools
import logging
import time
from pelix.constants import FrameworkException

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Logger
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory()
@Requires('_config', constants.SERVICE_CONFIGURATION)
@Requires('_leds', constants.SERVICE_LEDS)
@Requires('_nfc', constants.SERVICE_NFC)
@Requires('_publishers', constants.SERVICE_PUBLISHER, aggregate=True)
@Instantiate('vote-machine')
class VoteMachine(object):
    """
    Vote machine engine
    """
    def __init__(self):
        """
        Sets up members
        """
        # Vote values
        self.__values = []

        # NFC devices in use
        self.__nfc_devs = []

        # Configuration parser
        self._config = None

        # LEDs handler
        self._leds = None

        # NFC handler
        self._nfc = None

        # Vote publishers
        self._publishers = []


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Read configuration
        self.__values = self._config.getlist(constants.SECTION_VOTE,
                                             constants.VOTE_VALUES,
                                             constants.VOTE_VALUES_DEFAULT)
        if not self.__values:
            # Stop framework immediately
            raise FrameworkException("No vote values given in configuration",
                                     True)

        try:
            # Associate NFC devices and start listening
            self.associate_nfc()

        except (ValueError, IOError) as ex:
            # Error associating NFC devices
            raise FrameworkException("Error associating NFC devices: {0}"\
                                     .format(ex), True)


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        try:
            self.close()

        except Exception as ex:
            _logger.error("Error stopping the vote machine: %s", ex)


    def close(self):
        """
        Closes the MQTT connection and releases NFC devices
        """
        # Light down all LEDs
        for value in self.__values:
            self._leds.valid(value, False)
            self._leds.invalid(value, False)

        # Clean up NFC
        for clf in self.__nfc_devs:
            clf.close()
        del self.__nfc_devs[:]


    def associate_nfc(self):
        """
        Associates a NFC device with a vote value. Lights up the associated LEDs

        :raise ValueError: Not enough NFC devices
        """
        # Close currently used devices
        self.close()

        # Get all known devices
        nfc_devices = self._nfc.get_devices()
        if len(nfc_devices) < len(self.__values):
            raise ValueError("Not enough NFC devices found")

        _logger.info("Values: %s", self.__values)
        _logger.info("NFC devices: %s",
                     ', '.join(str(dev) for dev in nfc_devices))

        # vote value -> VoteDevice
        value_device = self.__associate(nfc_devices)

        # Prepare callbacks
        for value, device in value_device.items():
            # Prepare the NFC front end
            device.on_tag = functools.partial(self.__on_vote_tag, value)
            device.listen()


    def __associate(self, nfc_devices):
        """
        The NFC association loop

        :param nfc_devices: Available NFC devices
        :return: A dictionary: vote value -> NFC device
        """
        value_device = {}
        remaining_devices = list(nfc_devices)

        for idx, value in enumerate(self.__values):
            if idx > 0:
                # Wait a bit so that the user removes the tag from the device
                time.sleep(.3)

            _logger.info("Associating value %s...", value)
            # Lights up LED
            self._leds.valid(value, False)
            self._leds.invalid(value, True)

            # Associate a device
            _logger.info("Waiting for a tag...")
            device = self._nfc.wait_any_tag(remaining_devices)
            value_device[value] = device
            _logger.info("Using tag: %s", device)

            # Remove the device from the list
            remaining_devices.remove(device)

            # Blink
            self._leds.blink(value, True, 1)

            # Change LED state
            self._leds.valid(value, True)
            self._leds.invalid(value, False)

        _logger.info("All values associated")

        return value_device


    def __notify_vote(self, vote_vars):
        """
        Notifies all listeners that a vote occurred

        :param vote_vars: A dictionary containing vote variables
        """
        for publisher in self._publishers[:]:
            try:
                publisher.notify_vote(vote_vars.copy())

            except Exception as ex:
                _logger.exception("Error notifying a vote publisher: %s", ex)


    def __on_vote_tag(self, value, tag):
        """
        Vote tag handling (called by NFCpy)

        :param value: Vote value
        :param tag: Detected tag
        """
        # Light up the LED
        self._leds.valid(value, True)

        try:
            # Prepare payload variables
            variables = {  # Time stamp, in seconds
                         "timestamp": int(time.time()),
                         # Tag UID
                         "nfc_uid": str(tag.uid).encode("hex"),
                         # Vote value
                         "value": value}

            # Publish the vote
            self.__notify_vote(variables)

            # Blink the green LED
            self._leds.blink(value, True, 3)

            # Light up the green LED
            self._leds.valid(value, True)

        except Exception as ex:
            _logger.exception("Error handling vote: %s", ex)

            # Light down green LED
            self._leds.valid(value, False)

            # Warning LED
            self._leds.blink(value, False, 3)

            # Light down red LED
            self._leds.invalid(value, False)
            self._leds.valid(value, True)
