"""List 4-aligned literal words in HOMETOWN.BIN that point into 1ST_READ code (0x8c010000-0x8c200000) with their offsets"""
import sys, os, struct, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
lim = 0x4000 if len(sys.argv) < 2 else int(sys.argv[1], 16)
c = collections.defaultdict(list)
for i in range(0, lim, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if 0x8c010000 <= v < 0x8c200000:
        c[v].append(i)
for v in sorted(c):
    print('%08x x%d %s' % (v, len(c[v]), ' '.join('%x' % o for o in c[v][:12])))
