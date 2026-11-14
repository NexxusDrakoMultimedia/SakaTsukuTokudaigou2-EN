"""s7t: find 32-bit absolute pointers to a file offset inside an overlay. usage: file off"""
import os
import struct, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/tools')
import overlay
f, off = sys.argv[1], int(sys.argv[2], 0)
d = open(f, 'rb').read()
info = overlay.unpack_overlay(d)
base = info['load_addr']
print('base 0x%x entry 0x%x' % (base, info['entry']))
t = struct.pack('<I', base + off)
o = 0
while True:
    o = d.find(t, o)
    if o < 0:
        break
    print('ptr at file 0x%x (va 0x%x)' % (o, base + o))
    o += 1
