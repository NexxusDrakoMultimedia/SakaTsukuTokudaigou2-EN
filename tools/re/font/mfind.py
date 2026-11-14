"""usage: mfind.py OVERLAY hexoff... : find mov.w @(d,PC) loads of those values in an overlay"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sh4dis import *
img = load_overlay(sys.argv[1]); d = img.d
vals = [int(x,16) for x in sys.argv[2:]]
for o in range(0,len(d)-1,2):
    w=struct.unpack_from('<H',d,o)[0]
    if w>>12==9:
        ea=o+4+2*(w&0xff)
        if ea+2<=len(d):
            v=struct.unpack_from('<H',d,ea)[0]
            if v in vals: print(hex(img.base+o),hex(v))
