#!/usr/bin/python
# -- Content-Encoding: UTF-8 --

# Paho MQTT client
import paho.mqtt.client as paho

# libusb Python binding
import usb

# NFCpy
import nfc

# Standard library
import functools
import signal
import threading
import time

try:
    # Python 2
    import ConfigParser as configparser
except ImportError:
    # Python 3
    import configparser

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
                matching.append(usb_ident)

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

        print('[[ {0} pin {1} ]]'.format(pin, state_str))

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
            print("No green LED for {0}".format(value))
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
            print("No green LED for {0}".format(value))
        else:
            self._led_change(pin, state)

# ------------------------------------------------------------------------------

class VotingMachine(object):
    """
    Voting machine engine
    """
    def __init__(self):
        """
        Sets up members
        """
        # NFC front ends
        self.__nfc_devs = []

        # MQTT Client connection
        self.__mqtt = None

        # LEDs handling
        self.__leds = VoteLED()

    def close(self):
        """
        Closes the MQTT connection and releases NFC devices
        """
        # TODO: Clean up NFC

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
        remaining_devices = nfc_device_lookup()
        if len(remaining_devices) < len(vote_values):
            raise ValueError("Not enough NFC devices found")

        # vote value -> (busId, deviceId)
        value_device = {}

        for value in vote_values:
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
            clf = nfc.ContactlessFrontend('usb:{0}:{1}'.format(device[0],
                                                               device[1]))
            clf.connect(rdwr={'on-connect':
                              functools.partial(self.__on_vote_tag, value)})

            # Store it
            self.__nfc_devs.append(clf)

    def __on_vote_tag(self, value, tag):
        """
        Vote tag handling (called by NFCpy)

        :param value: Vote value
        :param tag: Detected tag
        """
        # Light up the LED
        self.__leds.valid(value, True)

        # Get vote ID
        id_vote = tag.ndef.message[0].data

        # Format the content
        payload = "{0} {1}".format(id_vote[-4:], value)

        # TODO: Send the message
        # self.__mqtt.publish('vote', payload)
        print(">>> Publishing vote: {0}".format(payload))

        # Wait a bit
        time.sleep(2)

        # Light down the LED
        self.__leds.valid(value, False)

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

        :param devices: A list of (busId, deviceId) tuples
        :return: The first device which detected a tag
        """
        # Tag reception event
        event = DataEvent()

        # List of ContactlessFrontend objects in use
        frontends = []

        for device in devices:
            # Prepare the front ends
            clf = nfc.ContactlessFrontend('usb:{0}:{1}'.format(device[0],
                                                               device[1]))
            clf.connect(rdwr={'on-connect':
                              functools.partial(self.__on_association_tag,
                                                event, device)})
            frontends.append(clf)

        # Wait for a tag...
        event.wait()

        # Clean up all front ends
        for clf in frontends:
            clf.close()

        # Return the tagged device
        return event.get_data()

# ------------------------------------------------------------------------------

def main(config):
    """
    Entry point

    :param config: A ConfigParser object
    """
    # Get vote values
    values = [value.strip()
              for value in config.get('vote', 'values').split(',')]
    if not values:
        print('No values given in configuration')
        return 1

    # Get LEDs configuration
    value_leds = {}
    for value in values:
        value_leds[value] = tuple(int(pin.strip()) \
                          for pin in config.get('leds', value, '').split(','))

    # Prepare the vote machine
    vote = VotingMachine()
    vote.connect_mqtt(config.get('mqtt', 'host', 'localhost'),
                      config.getint('mqtt', 'port', 1883))
    vote.setup_leds(value_leds)

    # Associate tags
    vote.associate_nfc(values)

    # Prepare the event we wait to stop
    event = threading.Event()

    # Register to signals
    def on_signal(signum):
        # Got a signal
        event.set()

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        try:
            signal.signal(signum, on_signal)
        except ValueError:
            # Unknown signal (Windows...)
            pass

    # Wait until the end of the vote (signal or KeyboardInterrupt)
    try:
        event.wait()
    except KeyboardInterrupt:
        print('Keyboard interruption... stopping')

    # Clean up
    vote.close()

if __name__ == '__main__':
    # Script entry point
    import sys

    # Read configuration
    config = configparser.RawConfigParser()
    config.read("vote.ini")

    # Run the vote machine
    sys.exit(main(config))
