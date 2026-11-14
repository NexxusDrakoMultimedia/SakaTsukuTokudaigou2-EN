"""fw_ram.py DUMP ADDR_HEX LEN_HEX [WIDTH] : hex dump of a Flycast RAM dump (16 MB from 0x8c000000), read-only; `*ADDR` derefs a u32 first."""
import struct, sys
dump, a, n = sys.argv[1], sys.argv[2], int(sys.argv[3], 16)
w = int(sys.argv[4]) if len(sys.argv) > 4 else 16
d = open(dump, 'rb').read()
if a.startswith('*'):
    p = int(a[1:], 16) - 0x8c000000
    a = '%x' % struct.unpack('<I', d[p:p + 4])[0]
    print('deref -> 0x%s' % a)
s = int(a, 16) - 0x8c000000
for i in range(0, n, w):
    c = d[s + i:s + i + w]
    print('%08x  %-*s  %s' % (0x8c000000 + s + i, w * 3, ' '.join('%02x' % b for b in c), ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)))
