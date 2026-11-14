"""s7p_stats - per-row ink statistics and colour census of the original club-name plates (ALLLOGOS [0..65]).
usage: s7p_stats.py"""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
import numpy as np
import s7p_dump as D

cols = collections.Counter()
rows = []
for k in range(66):
    img = D.to_img(D.load('GAME/ALLLOGOS.BIN', '[%d]' % k))
    for r in range(4):
        cell = img[r * 32:(r + 1) * 32]
        a = cell[..., 3] > 0
        if not a.any():
            rows.append((k, r, None)); continue
        ys = np.where(a.any(1))[0]; xs = np.where(a.any(0))[0]
        rows.append((k, r, (ys[0], ys[-1], xs[0], xs[-1])))
        for px in cell[a].reshape(-1, 4):
            cols[tuple(px)] += 1
print('colours:', cols.most_common(14))
tot = sum(cols.values())
print('distinct', len(cols), 'ink px', tot)
ys0 = [r[2][0] for r in rows if r[2]]; ys1 = [r[2][1] for r in rows if r[2]]
print('top y min/med/max', min(ys0), sorted(ys0)[len(ys0)//2], max(ys0), 'bottom', min(ys1), sorted(ys1)[len(ys1)//2], max(ys1))
xs0 = [r[2][2] for r in rows if r[2]]; xs1 = [r[2][3] for r in rows if r[2]]
print('left min', min(xs0), 'right max', max(xs1))
for k in (0, 2, 5, 8, 59):
    print(k, [r[2] for r in rows if r[0] == k])
