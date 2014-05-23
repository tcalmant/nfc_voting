#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Configuration parser and writer service

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Local
import constants

# Pelix
from pelix.constants import BundleActivator

# Standard library
import logging

try:
    # Python 2
    import ConfigParser as configparser

except ImportError:
    # Python 3
    import configparser

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Logger
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class Configuration(object):
    """
    Configuration utility wrapper
    """
    def __init__(self):
        """
        Sets up the wrapper
        """
        # Dummy configuration
        self.config = configparser.RawConfigParser()

        # Dirty configuration flag
        self.__dirty = False


    @property
    def dirty(self):
        """
        Checks if the configuration file needs to be written
        """
        return self.__dirty


    def load(self, filename=constants.CONFIG_FILE):
        """
        Loads the content of a configuration file

        :param filename: The configuration file name
        """
        self.config = configparser.RawConfigParser()
        self.config.read(filename)


    def save(self, filename=constants.CONFIG_FILE):
        """
        Saves the configuration file

        :param filename: The configuration file name
        """
        try:
            with open(filename, "w") as fp:
                self.config.write(fp)

        except IOError as ex:
            _logger.error("Error writing configuration file: %s", ex)

        else:
            # Configuration stored
            self.__dirty = False
            _logger.info("Configuration saved.")


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
        self.__dirty = True

# ------------------------------------------------------------------------------

@BundleActivator
class _Activator(object):
    """
    Pelix bundle activator
    """
    def __init__(self):
        """
        Sets up members
        """
        self.registration = None
        self.service = None

    def start(self, context):
        """
        Bundle started: registers the service
        """
        # Prepare the service and load the existing configuration
        self.service = Configuration()
        self.service.load()
        self.registration = context.register_service(
                                             constants.SERVICE_CONFIGURATION,
                                             self.service, {})

    def stop(self, context):
        """
        Bundle stopped: clean up
        """
        # Unregister the service
        self.registration.unregister()

        self.registration = None
        self.service = None
