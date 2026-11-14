"""hng: list 4-aligned literal words of an overlay in an address range with the file offsets of the pool words.
usage: hng_litrange.py OVERLAY LO HI [BASE]"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import hng_dis
n, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
base = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x8c2d0000
d = hng_dis.load(n)
for i in range(0, len(d) - 3, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if lo <= v < hi:
        users = [o for o in range(max(0, i - 1100), min(len(d) - 1, i + 2), 2)
                 if (struct.unpack_from('<H', d, o)[0] >> 12) == 0xD and ((o + 4) & ~3) + (struct.unpack_from('<H', d, o)[0] & 0xFF) * 4 == i]
        print('%#x: %#x  users %s' % (base + i, v, [hex(base + u) for u in users]))
