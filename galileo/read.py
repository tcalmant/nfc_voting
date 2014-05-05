import nfc
import time
import sys
import paho.mqtt.client as mosquitto

def nfc_device_lookup(nfc_dev=(0x04E6, 0x5591)):
    """
    Looks for known NFC devices
    
    :param nfc_dev: A USB device identification tuple
                    (vendor, product)
    :return: A list of (bus, device) tuples for connected devices
    """
    # python-usb
    import usb
  
    # For each USB bus
    for bus in usb.busses():
	# For each device
	for dev in bus.devices:
	    # Check if the device matches the USB identifier
	    usb_ident = (dev.idVendor, dev.idProduct)
	    if usb_ident == NFC_DEV:
		found.append(usb_ident)

    return found

def connected(tag):
  try:
    id_vote = tag.ndef.message[0].data
    print tag
    global vote
    #connect to the mqtt broker and publish the vote
    mqttc = mosquitto.Mosquitto("pyt")
    mqttc.connect("127.0.0.1", 1883, 60)
    mqttc.publish('vote', id_vote[-4:] + ' ' + vote, 1)

    print 'The vote '+vote+' was successful'
    time.sleep(3)
    global clf
    clf.connect(rdwr={'on-connect': connected})
    return True
  except:
    print "Unexpected error:", sys.exc_info()[0]
    print 'Error during the transmission of the vote'
    return True

if len(sys.argv) != 3:
  print 'Usage : read.py [usb_id] [vote_value]'
  print 'To find the usb_id use lsusb and pick the two numbers identifying the device'
  print 'The vote value can be 0, 1 or 2'
  exit(0)

id1 = sys.argv[1]
vote = sys.argv[2]

#link the handler to the reading of a tag
clf = nfc.ContactlessFrontend('usb:'+id1)
clf.connect(rdwr={'on-connect': connected})

while True:
  pass
