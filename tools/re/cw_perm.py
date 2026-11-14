"""Find byte/short/int arrays that look like a permutation / index table of 50..60 entries in a FLOW_PRG overlay.
usage: cw_perm.py FILE [minlen=45]"""
import sys, struct
d = open(sys.argv[1], 'rb').read()
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 45
for w, fmt in ((1, 'B'), (2, '>H'), (4, '>I'), (2, '<H'), (4, '<I')):
    step = 1 if w == 1 else w
    i = 0
    n = len(d)
    while i + w*minlen <= n:
        vals = []
        j = i
        seen = set()
        while j + w <= n:
            v = struct.unpack_from(fmt if w > 1 else 'B', d, j)[0]
            if v > 70 or v in seen: break
            seen.add(v); vals.append(v); j += w
        if len(vals) >= minlen:
            print(fmt, hex(i), len(vals), vals[:70])
            i = j
        else:
            i += w if w > 1 else 1
