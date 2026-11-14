"""s8fg: find 32-bit LE words in FILE equal to given values (hex). usage: s8fg_findw.py FILE VAL..."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
for v in sys.argv[2:]:
    t = int(v, 16)
    hits = [hex(o) for o in range(0, len(d) - 3, 2) if struct.unpack_from('<I', d, o)[0] == t]
    print(v, hits)
