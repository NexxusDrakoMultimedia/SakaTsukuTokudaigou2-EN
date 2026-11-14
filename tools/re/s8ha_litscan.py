"""s8ha: find 4-aligned longs in [LO, HI) (RAM addresses) in extracted/1ST_READ.BIN and every extracted overlay (read-only).  usage: s8ha_litscan.py LO HI"""
import glob, os, struct, sys
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
files = ['extracted/1ST_READ.BIN'] + sorted(glob.glob('extracted/FLOW_PRG/*.BIN'))
for f in files:
    d = open(f, 'rb').read()
    n = len(d) // 4
    hits = []
    for i in range(n):
        v = struct.unpack_from('<I', d, 4 * i)[0]
        if lo <= v < hi:
            hits.append('%x:%08x' % (4 * i, v))
    if hits:
        print(os.path.basename(f), len(hits), hits[:12])
