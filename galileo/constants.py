#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Vote machine configuration constants

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

SERVICE_LEDS = "leds.controller"
""" Specification of the LEDs controller """

SERVICE_NFC = "nfc.controller"
""" Specification of the NFC controller """

SERVICE_CONFIGURATION = "vote.configuration"
""" Specification of the vote configuration parser """

SERVICE_PUBLISHER = "vote.publisher"
""" Specification of a vote publisher (publishes vote information) """

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

# ... MQTT topic
MQTT_TOPIC = "topic"
MQTT_TOPIC_DEFAULT = "vote"

# ... MQTT payload
MQTT_PAYLOAD = "payload"
MQTT_PAYLOAD_DEFAULT = "{timestamp},{nfc_uid},{value}"

# ... values in the vote (comma-separated list)
VOTE_VALUES = "values"
VOTE_VALUES_DEFAULT = (0, 1, 2)
