"""Read-only: u16 at address of 1ST_READ.BIN. usage: dxp_peek16.py ADDR"""
import sys, struct
d = open('extracted/1ST_READ.BIN', 'rb').read()
a = int(sys.argv[1], 16)
print('%08x: %04x (%d)' % (a, struct.unpack_from('<H', d, a - 0x8c010000)[0], struct.unpack_from('<H', d, a - 0x8c010000)[0]))
