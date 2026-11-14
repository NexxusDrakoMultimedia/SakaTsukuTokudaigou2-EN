"""skh: list 32-bit literals of a file whose value lies in [LO, HI) (hex), with file offsets.  usage: skh_litrange.py FILE LO HI  (FILE: overlay name like EVENT or a path)"""
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = sys.argv[1]
p = spec if os.path.isfile(spec) else os.path.join(ROOT, 'extracted', 'FLOW_PRG', spec + '.BIN')
d = open(p, 'rb').read()
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
c = Counter()
offs = {}
for o in range(0, len(d) - 3, 4):
    v = struct.unpack_from('<I', d, o)[0]
    if lo <= v < hi:
        c[v] += 1
        offs.setdefault(v, []).append(o)
for v in sorted(c):
    print('%#x x%d  %s' % (v, c[v], ' '.join('%#x' % x for x in offs[v][:6])))
