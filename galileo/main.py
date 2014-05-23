#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
NFC vote machine

:authors: Antoine GERVAIL, Amine ZIAN­CHERIF, Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Pelix
from pelix.framework import create_framework

# Standard library
import logging

# ------------------------------------------------------------------------------

def main():
    """
    Entry point

    :return: An exit code (0 for success)
    """
    framework = create_framework(('pelix.ipopo.core',
                                  'pelix.shell.core',
                                  'pelix.shell.ipopo',
                                  'pelix.shell.console',
                                  'configuration',
                                  'leds',
                                  'publisher_mqtt',
                                  'nfc_wrapper',
                                  'vote_machine'))

    try:
        # Start the framework
        logging.warning("Starting framework...")
        framework.start()

    except Exception as ex:
        logging.exception("Error starting framework: %s", ex)

        # Stop the framework
        try:
            framework.stop()
        except:
            pass

        return 1

    try:
        # Wait for the framework to stop
        logging.info("Waiting for the framework to stop...")
        framework.wait_for_stop()

    except KeyboardInterrupt:
        # User wants to go
        logging.info("Exiting on Ctrl+C...")

        try:
            framework.stop()
        except:
            pass

    logging.info("Bye !")
    return 0

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # Script entry point
    import sys

    # Setup logs
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("nfc").setLevel(logging.CRITICAL)

    # Run the vote machine
    sys.exit(main())
