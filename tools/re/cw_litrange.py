"""Find literals in range [lo,hi] (absolute addresses) in an overlay. usage: cw_litrange.py FILE LO HI"""
import sys, struct
d = open(sys.argv[1], 'rb').read(); lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16)
for i in range(0, len(d)-3, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if lo <= v <= hi: print('%x: %08x' % (i, v))
