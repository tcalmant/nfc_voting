#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Vote machine configuration constants

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

try:
    # Python 2
    import ConfigParser as configparser

except ImportError:
    # Python 3
    import configparser

# ------------------------------------------------------------------------------

# Configuration file name
CONFIG_FILE = "vote.ini"

# Sections
SECTION_MQTT = "mqtt"
SECTION_VOTE = "vote"
SECTION_LEDS = "leds"

# Entries & Default values
# ... MQTT server host
MQTT_HOST = "host"
MQTT_HOST_DEFAULT = "localhost"

# ... MQTT server port
MQTT_PORT = "port"
MQTT_PORT_DEFAULT = 1883

# ... values in the vote (comma-separated list)
VOTE_VALUES = "values"
VOTE_VALUES_DEFAULT = (0, 1, 2)

# ------------------------------------------------------------------------------

class Configuration(object):
    """
    Configuration utility wrapper
    """
    def __init__(self, config_file=CONFIG_FILE):
        """
        Sets up the wrapper

        :param config_file: The configuration file name
        """
        # Configuration
        self.config = configparser.RawConfigParser()
        self.config.read(config_file)

        # Filename
        self.__config_file = config_file

        # Dirty configuration flag
        self.dirty = False


    def get(self, section, option, default):
        """
        Gets the value of the configuration option, or returns the given default

        :param section: Configuration section
        :param option: Option in section
        :param default: Value to return if option doesn't exist
        :return: The configuration value or the default one
        """
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            # Missing
            return default


    def getint(self, section, option, default):
        """
        Gets the value of the configuration option, or returns the given default

        :param section: Configuration section
        :param option: Option in section
        :param default: Value to return if option doesn't exist
        :return: The configuration value or the default one
        """
        try:
            return int(self.config.get(section, option))
        except (configparser.NoSectionError, configparser.NoOptionError,
                ValueError):
            # Missing or invalid
            return default


    def getlist(self, section, option, default):
        """
        Returns a list, stored as a comma-separated list

        :param section: Configuration section
        :param option: Option in section
        :param default: Value to return if option doesn't exist
        :return: The list from the configuration or the default value
        """
        try:
            raw_list = self.config.get(section, option).split(',')

        except (configparser.NoSectionError, configparser.NoOptionError):
            # Missing
            return default

        else:
            return [item.strip() for item in raw_list if item.strip()]


    def set(self, section, option, value):
        """
        Sets the value of a configuration option. Creates the section if needed

        :param section: Configuration section
        :param option: Option in section
        :param value: Value to store
        """
        if not self.config.has_section(section):
            # Create the section
            self.config.add_section(section)

        # Normalize the value
        if value is not None:
            value = str(value)

        # Store it
        self.config.set(section, option, value)

        # Configuration changed
        self.dirty = True


    def save(self):
        """
        Saves the configuration file
        """
        try:
            with open(self.__config_file, "w") as fp:
                self.config.write(fp)
        except IOError as ex:
            print("Error writing configuration file: {0}".format(ex))
        else:
            # Configuration stored
            self.dirty = False
            print("Configuration saved.")
