"""hng: hex dump of an extracted overlay range.  usage: hng_peek.py OVERLAY FILEOFF LEN"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hng_dis
d = hng_dis.load(sys.argv[1]); a = int(sys.argv[2], 16); n = int(sys.argv[3], 16)
for o in range(a, a + n, 16):
    row = d[o:o + 16]
    print('%08x  %s  %s' % (o, row.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))
