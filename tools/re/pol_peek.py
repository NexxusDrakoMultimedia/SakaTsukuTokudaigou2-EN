"""pol: print town table entries k of a built HOMETOWN.BIN: python -I -X utf8 tools/re/pol_peek.py HOMETOWN.BIN k [k ...]"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
for k in map(int, sys.argv[2:]):
    p = struct.unpack_from('<I', d, 0x43854 + 4 * k)[0]
    off = p - 0x8c2d0000
    print(k, hex(p), hex(off), d[off:d.index(b'\0', off)])
