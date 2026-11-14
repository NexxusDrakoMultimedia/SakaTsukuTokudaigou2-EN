"""fw_hexdump.py FILE START_HEX LEN_HEX [WIDTH]: plain hex+ascii dump of a file range (read-only)."""
import sys
f, s, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
w = int(sys.argv[4]) if len(sys.argv) > 4 else 16
d = open(f, 'rb').read()[s:s + n]
for i in range(0, len(d), w):
    c = d[i:i + w]
    print('%06x  %-*s  %s' % (s + i, w * 3, ' '.join('%02x' % b for b in c), ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)))
