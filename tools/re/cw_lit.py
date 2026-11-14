"""Find 32-bit big/little literals in an overlay. usage: cw_lit.py FILE HEXVALUE"""
import sys, struct
d = open(sys.argv[1], 'rb').read(); v = int(sys.argv[2], 16)
for fmt in ('<I', '>I'):
    b = struct.pack(fmt, v)
    i = d.find(b)
    while i >= 0:
        print(fmt, hex(i)); i = d.find(b, i+1)
