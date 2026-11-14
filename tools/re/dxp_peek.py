"""Read-only: print u32 words of 1ST_READ.BIN at given load addresses. usage: dxp_peek.py ADDR [N]"""
import sys, struct
d = open('extracted/1ST_READ.BIN', 'rb').read()
a = int(sys.argv[1], 16); n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for i in range(n):
    off = a - 0x8c010000 + 4 * i
    print('%08x: %08x' % (a + 4 * i, struct.unpack_from('<I', d, off)[0]))
