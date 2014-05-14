#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Generates the configuration of the vote machine

:authors: Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# Configuration constants
import constants

try:
    # Python 2
    prompt = raw_input

except (ImportError, NameError):
    # Python 3
    prompt = input

# ------------------------------------------------------------------------------

class ConfigurationMenu(object):
    """
    Vote machine configuration menu
    """
    def __init__(self):
        """
        Set up members
        """
        # Parse existing configuration
        self.config = constants.Configuration()

        # List of screens
        self.main_screen_name = "Main menu"
        self.screens = ((self.main_screen_name, self.menu_main),
                        ("MQTT configuration", self.menu_mqtt),
                        ("Vote configuration", self.menu_vote))


    def __print_menu(self, choices):
        """
        Prints a menu and returns the raw user choice

        :param choices: A (key -> text) list (printed in the given order)
        """
        str_keys = [str(choice[0]) for choice in choices]

        for key, name in choices:
            print("{0}. {1}".format(key, name))

        while True:
            choice = prompt("Selection: ").strip()
            if choice not in str_keys:
                print("Unknown choice: '{0}'".format(choice))
            else:
                return choice


    def __print_int_menu(self, choices):
        """
        Prints a menu with integer selections

        :param choices: A (key -> text) list (printed in the given order)
        """
        while True:
            try:
                # Print menu and convert result
                return int(self.__print_menu(choices))
            except ValueError:
                # Invalid choice
                print("Invalid choice")


    def menu_main(self):
        """
        Main menu
        """
        choices = [(idx, screen[0])
                   for idx, screen in enumerate(self.screens)
                   if idx != 0]
        choices.append(('w', 'Write configuration file'))
        choices.append(('q', 'Quit'))

        # Reprint
        reprint = False
        next_menu = None

        while True:
            if reprint and next_menu:
                reprint = next_menu()

            else:
                choice = self.__print_menu(choices)
                if choice == 'q':
                    # Quit
                    if self.config.dirty:
                        while choice not in ('y', 'n'):
                            choice = prompt("Save modifications ? (y/n)")\
                                        .lower()
                            if choice == 'y':
                                self.config.save()
                            elif choice == 'n':
                                break

                    return

                elif choice == 'w':
                    # Save file
                    self.config.save()

                else:
                    try:
                        choice = int(choice)
                        if choice < 1:
                            # 0 and negative choices are forbidden
                            raise ValueError()

                        # Get next menu
                        next_menu = self.screens[choice][1]

                    except (ValueError, IndexError):
                        print("Error: Invalid selection")

                    else:
                        # Show the next menu
                        reprint = next_menu()


    def menu_mqtt(self):
        """
        MQTT configuration
        """
        # Get current values
        host = self.config.get(constants.SECTION_MQTT, constants.MQTT_HOST,
                               constants.MQTT_HOST_DEFAULT)
        port = self.config.getint(constants.SECTION_MQTT, constants.MQTT_PORT,
                                  constants.MQTT_PORT_DEFAULT)

        # Print menu
        choices = ((0, self.main_screen_name),
                   (1, "Change host ({0})".format(host)),
                   (2, "Change port ({0})".format(port)))
        choice = self.__print_int_menu(choices)

        if choice == 0:
            # Back to main menu
            return False

        elif choice == 1:
            # Change host
            host = prompt("MQTT Server Host ({0}): " \
                          .format(constants.MQTT_HOST_DEFAULT)).strip() \
                    or constants.MQTT_HOST_DEFAULT

            self.config.set(constants.SECTION_MQTT, constants.MQTT_HOST, host)

        elif choice == 2:
            # Change port
            port = prompt("MQTT Server Port:").strip() \
                    or constants.MQTT_PORT_DEFAULT
            try:
                port = int(port)
            except ValueError:
                print('Invalid port')
            else:
                self.config.set(constants.SECTION_MQTT, constants.MQTT_PORT,
                                port)

        return True


    def menu_vote(self):
        """
        Vote configuration
        """
        # Get current values
        values = self.config.get(constants.SECTION_VOTE, constants.VOTE_VALUES,
                                 constants.VOTE_VALUES_DEFAULT)

        # Print menu
        choices = ((0, self.main_screen_name),
                   (1, "Change values ({0})".format(values)),
                   (2, "Change LEDs"))
        choice = self.__print_int_menu(choices)

        if choice == 0:
            # Back to main menu
            return False

        elif choice == 1:
            # Change values
            values = prompt("Vote values (comma-separated): ")
            values = ','.join(value.strip()
                              for value in values.split(',') if value.strip())
            if not values:
                values = constants.VOTE_VALUES_DEFAULT

            self.config.set(constants.SECTION_VOTE, constants.VOTE_VALUES,
                            values)

        elif choice == 2:
            # Change LEDs
            reprint = True
            while reprint:
                reprint = self.menu_led()

        return True


    def menu_led(self):
        """
        LEDs configuration
        """
        # Get vote values
        values = self.config.getlist(constants.SECTION_VOTE,
                                     constants.VOTE_VALUES,
                                     constants.VOTE_VALUES_DEFAULT)

        # Get LEDs
        value_leds = {}
        for value in values:
            value_leds[value] = self.config.get(constants.SECTION_LEDS,
                                                value, "")

        # Print menu
        choices = [(0, "Back to vote menu")]
        choices.extend((idx + 1, "Value: {0} ({1})" \
                                 .format(value, value_leds[value]))
                        for idx, value in enumerate(values))
        choice = self.__print_int_menu(choices)
        if choice == 0:
            # Back to previous menu
            return False

        else:
            # Change LEDs for value
            value = choice - 1
            leds = prompt("LEDs pins (green, red): ")
            leds = ','.join(led.strip()
                            for led in leds.split(',') if led.strip())
            self.config.set(constants.SECTION_LEDS, str(value), leds)

        return True

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    menu = ConfigurationMenu()

    try:
        menu.menu_main()
    except (KeyboardInterrupt, EOFError):
        pass

    print("Bye !")
