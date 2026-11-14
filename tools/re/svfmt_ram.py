"""svfmt_ram.py DUMP ADDR [LEN] [--ptr] : hexdump of RAM dump (base 0x8c000000); with --ptr first dereference a 32-bit pointer at ADDR."""
import sys, os, struct
args = [a for a in sys.argv[1:] if not a.startswith('--')]
d = open(args[0], 'rb').read()
def w(a): return struct.unpack_from('<I', d, a - 0x8c000000)[0]
a = int(args[1], 16); n = int(args[2], 16) if len(args) > 2 else 0x40
if '--ptr' in sys.argv:
    a = w(a); print('ptr ->', hex(a))
for o in range(0, n, 16):
    b = d[a - 0x8c000000 + o: a - 0x8c000000 + o + 16]
    print('%08x ' % (a + o) + ' '.join('%02x' % x for x in b) + '  ' + ''.join(chr(x) if 32 <= x < 127 else '.' for x in b))
