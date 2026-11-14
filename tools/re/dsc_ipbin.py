"""dsc_ipbin: print the IP.BIN fields verify_disc checks (read-only).  python -I -X utf8 tools/re/dsc_ipbin.py"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D

s = D.Source('.')
ip = s.read(D.HD_BASE, 16 * 2048)
print(ip[:0x40])
print('crc field', ip[0x20:0x24], 'prod/ver', ip[0x40:0x50])
print('boot name @0x60', ip[0x60:0x70])
for off in range(0x100, 0x2A0, 4):
    v, = struct.unpack_from('<I', ip, off)
    if v:
        print('0x%03x 0x%08x' % (off, v))
