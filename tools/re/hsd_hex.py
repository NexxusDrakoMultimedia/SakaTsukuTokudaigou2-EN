"""hsd: hexdump a range of a file.  usage: hsd_hex.py FILE LO HI (hex).  Read-only."""
import sys
d = open(sys.argv[1], 'rb').read()
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
for i in range(lo, hi, 16):
    c = d[i:i+16]
    print('%06x  %s  %s' % (i, ' '.join('%02x' % x for x in c), ''.join(chr(x) if 32 <= x < 127 else '.' for x in c)))
