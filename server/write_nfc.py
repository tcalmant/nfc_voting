#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
NFC tag writer: sets up the tag read by the voting machine

:authors: Antoine GERVAIL, Amine ZIAN­CHERIF, Thomas CALMANT
:license: Eclipse Public License 1.0
"""

# nfcpy
import nfc.ndef

# Standard library
import functools
import sys

def connected(id_num, tag):
    sp = nfc.ndef.TextRecord(str(id_num))
    sp.name = 'id'
    tag.ndef.message = nfc.ndef.Message(sp)
    print("ID set: {0}".format(id_num))
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: write_nfc.py [id]"
        sys.exit(0)

    id_num = int(sys.argv[1])
    clf = nfc.ContactlessFrontend('usb')
    tag = clf.connect(rdwr={'on-connect':
                            functools.partial(connected, id_num)})
