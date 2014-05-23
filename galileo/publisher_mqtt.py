#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Vote notification service using MQTT

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Local
import constants

# Pelix MQTT client (based on Paho)
import pelix.misc.mqtt_client as mqtt

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Instantiate, Validate, \
    Invalidate, Provides, Requires

# Standard library
import logging

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
@Provides(constants.SERVICE_PUBLISHER, controller='_controller')
@Requires('_config', constants.SERVICE_CONFIGURATION)
@Instantiate('mqtt-notifier')
class MqttNotifier(object):
    """
    MQTT notification service
    """
    def __init__(self):
        """
        Sets up members
        """
        # self._configuration parser
        self._config = None

        # Service controller
        self._controller = False

        # MQTT client
        self._mqtt = None

        # Topic & payload format
        self._topic = None
        self._payload = None


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # MQTT server
        host = self._config.get(constants.SECTION_MQTT,
                                constants.MQTT_HOST,
                                constants.MQTT_HOST_DEFAULT)
        port = self._config.getint(constants.SECTION_MQTT,
                                   constants.MQTT_PORT,
                                   constants.MQTT_PORT_DEFAULT)

        # Message configuration
        self._topic = self._config.get(constants.SECTION_MQTT,
                                       constants.MQTT_TOPIC,
                                       constants.MQTT_TOPIC_DEFAULT)
        self._payload = self._config.get(constants.SECTION_MQTT,
                                         constants.MQTT_PAYLOAD,
                                         constants.MQTT_PAYLOAD_DEFAULT)

        # Connect the server
        self._controller = False
        client_id = mqtt.MqttClient.generate_id("nfcvote-")

        self._mqtt = mqtt.MqttClient(client_id)
        self._mqtt.on_connect = self.__on_connect
        self._mqtt.on_disconnect = self.__on_disconnect
        self._mqtt.connect(host, port)


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._controller = False

        # Disconnect from MQTT
        if self._mqtt is not None:
            self._mqtt.disconnect()
            self._mqtt = None


    def __on_connect(self, client, rc):
        """
        MQTT server connection result
        """
        if not rc:
            _logger.info("MQTT vote notifier connected")
            self._controller = True


    def __on_disconnect(self, client, rc):
        """
        Disconnected from the server
        """
        _logger.info("MQTT vote notifier disconnected")
        self._controller = False


    def notify_vote(self, vote_vars):
        """
        Publishes a message describing the vote

        :param vote_vars: Vote description dictionary
        """
        # Format the payload first
        payload = self._payload.format(**vote_vars)
        self._mqtt.publish(self._topic, payload, qos=2)
