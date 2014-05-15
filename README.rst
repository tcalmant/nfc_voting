.. NFC Voting Machine

NFC Voting Machine
##################

Uses an Intel Galileo as a voting machine, based on NFC tags and readers:

* Vote can have as many values as there are plugged NFC readers.
* Each tag detection results in a vote, its description is sent through MQTT
  (... vote uniqueness must be handled by the server-side)


This project is the continuation of the work of Antoine GERVAIL and
Amine ZIAN­CHERIF during their Master 2 at
`Université Joseph Fourier <http://ufrima.imag.fr/spip.php?rubrique12>`_,
Grenoble.


.. note:: The `original README file <README.original.md>`_ (in French)
   describes the architecture of the project.

.. note:: The original project is available at
   `twane/nfc_voting <https://github.com/twane/nfc_voting>`_

Dependencies
************

Galileo
=======

For the Galileo you need to use a Linux distribution (not the built-in one).

* Python
* `Python-nfcpy <https://launchpad.net/nfcpy>`_
* `Paho Python MQTT Client <http://www.eclipse.org/paho/>`_
* `Pelix/iPOPO <https://ipopo.coderxpress.net>`_

Server
======

.. note:: The server part is not maintained in this fork

* Python
* Python-nfcpy
* Python-pygame
* Paho Python MQTT Client
* NodeJS
* MongoDB


Installation
************

System configuration
====================

In order to use the NFC reader without problems, it is recommend to follow the
recommendations from the nfcpy documentation.

From http://nfcpy.readthedocs.org/en/latest/topics/get-started.html#installation

   Things may not immediately work on Linux for two reasons:
   The reader might be claimed by the Linux NFC subsystem available since
   Linux 3.1 and root privileges may be required to access the device.

   To prevent a reader being used by the NFC kernel driver add a blacklist
   entry in '/etc/modprobe.d/', for example the following line works for the
   PN533 based SCL3711:

     $ echo "blacklist pn533" | sudo tee -a /etc/modprobe.d/blacklist-nfc.conf


   Root permissions are usually needed for the USB readers and 'sudo python'
   is an easy fix, however not quite convenient and potentially dangerous.

   A better solution is to add a udev rule and make the reader accessible to a
   normal user, like the following rules would allow members of the
   'plugdev' group to access an SCL-3711 or RC-S380 if stored in
   '/etc/udev/rules.d/nfcdev.rules'.

   SUBSYSTEM=="usb", ACTION=="add", ATTRS{idVendor}=="04e6", \
     ATTRS{idProduct}=="5591", GROUP="plugdev" # SCM SCL-3711
   SUBSYSTEM=="usb", ACTION=="add", ATTRS{idVendor}=="054c", \
     ATTRS{idProduct}=="06c1", GROUP="plugdev" # Sony RC-S380


NFC readers can be plugged once the system has been configured.


Voting Machine
==============

Go in some directory on the Galileo's SD card and run the following commands:

.. code-block:: bash

   # Project source code
   wget https://github.com/tcalmant/nfc_voting/archive/master.zip
   unzip nfc_voting-master.zip
   
   # Go into the Galileo folder
   cd nfc_voting-master/galileo

   # Paho
   pip install paho-mqtt

   # Pelix/iPOPO
   pip install iPOPO

   # nfcpy
   wget https://launchpad.net/nfcpy/0.9/0.9.1/+download/nfcpy-0.9.1.tar.gz
   tar xf nfcpy-0.9.1.tar.gz
   mv nfcpy-0.9.1/nfc .
   rm -r nfcpy-0.9.1 nfcpy-0.9.1.tar.gz


The next step is to generate the configuration of the vote, using the
``make_config.py`` script. This will generate a file named ``vote.ini``.

Finally, you can run the vote machine running the ``vote_machine.py`` script.
It will first associate a NFC reader to a vote value, then the users will be
able to vote with their tags.
