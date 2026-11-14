"""ar6_rows: row groups of ink in a texture's left strip: ar6_rows.py ID XMAX -> (y0, y1, x0, x1) per run of ink rows"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import art7_lib as L
i, xmax = sys.argv[1], int(sys.argv[2])
a = L.load(i)['arr']
m = (a[:, :xmax, 3] > 100)
rows = np.nonzero(m.any(1))[0]
runs = []
s = p = rows[0]
for y in rows[1:]:
    if y > p + 1:
        runs.append((s, p)); s = y
    p = y
runs.append((s, p))
for s, e in runs:
    xs = np.nonzero(m[s:e + 1].any(0))[0]
    # split in x gaps > 4
    segs = []
    x0 = xp = xs[0]
    for x in xs[1:]:
        if x > xp + 5:
            segs.append((int(x0), int(xp))); x0 = x
        xp = x
    segs.append((int(x0), int(xp)))
    print(int(s), int(e), segs)
