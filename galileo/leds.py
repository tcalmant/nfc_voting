#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Controls LEDs using GPIO on sysfs

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Local
import constants

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Instantiate, Validate, \
    Invalidate, Provides, Requires

# Standard library
import logging
import math
import time

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
@Provides(constants.SERVICE_LEDS)
@Requires('_config', constants.SERVICE_CONFIGURATION)
@Instantiate('leds-handler')
class VoteLED(object):
    """
    Represents the LED(s) associated to a vote
    """
    def __init__(self):
        """
        Sets up the LED(s) wrapper
        """
        # Configuration parser
        self._config = None

        # Value -> (green, red)
        self.pins = {}


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Get vote values
        values = self._config.getlist(constants.SECTION_VOTE,
                                      constants.VOTE_VALUES,
                                      constants.VOTE_VALUES_DEFAULT)

        if values:
            # Get LEDs configuration
            value_leds = {}
            for idx, value in enumerate(values):
                value_leds[value] = tuple(int(pin) for pin \
                            in self._config.getlist(constants.SECTION_LEDS,
                                                    str(idx), []))

            # Configure the pins
            self.setup(value_leds)


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self.close()


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
                value_pins = tuple(pins)
            else:
                # Ensure we have a tuple
                value_pins = (pins,)

            # Store pins
            self.pins[value] = value_pins

            # Setup GPIO
            for pin in value_pins:
                try:
                    # ... Export
                    with open("/sys/class/gpio/export", "w") as fp:
                        fp.write(str(pin))

                    # ... Output mode
                    with open("/sys/class/gpio/gpio{0}/direction".format(pin),
                              "w") as fp:
                        fp.write("out")

                except IOError as ex:
                    _logger.error("Error exporting pin %s: %s", pin, ex)


    def close(self):
        """
        Cleans up the GPIO pins
        """
        # Clear storage
        all_pins = set()
        for value_pins in self.pins.values():
            all_pins.update(value_pins)
        self.pins.clear()

        # Unexport all pins
        for pin in all_pins:
            try:
                # ... Light down
                self._led_change(pin, False)

                # ... Unexport
                with open("/sys/class/gpio/unexport", "w") as fp:
                    fp.write(str(pin))

            except IOError as ex:
                _logger.warning("Error unexporting pin %s: %s", pin, ex)


    def _led_change(self, pin, state):
        """
        Lights up/down the LED at the given pin

        :param pin: LED pin
        :param state: If True, lights up, else lights down
        """
        # Compute GPIO value
        state_str = "1" if state else "0"

        try:
            # ... Update value
            with open("/sys/class/gpio/gpio{0}/value".format(pin), "w") as fp:
                fp.write(state_str)

        except IOError as ex:
            _logger.error("Error setting value of pin %s: %s", pin, ex)


    def blink(self, value, blink_valid, duration=3, pause=.3):
        """
        Makes a LED blink for some time (blocking)

        :param value: Vote value
        :param blink_valid: If True, makes the valid LED blink, else the invalid
        :param duration: Duration of the blink
        :param pause: Time the LED stays in a position
        """
        try:
            pin = self.pins[value][0 if blink_valid else 1]
            if pin is None:
                raise IndexError()

        except (KeyError, IndexError):
            # No LED for this value
            return

        nb_iterations = int(math.ceil(duration / pause))

        # First step: light on
        state = True
        self._led_change(pin, state)

        for _ in range(nb_iterations):
            # Wait a bit
            time.sleep(pause)

            # Revert state
            state = not state
            self._led_change(pin, state)

        # Light off
        self._led_change(pin, False)


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
