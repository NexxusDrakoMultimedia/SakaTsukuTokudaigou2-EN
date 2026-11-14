"""s7g_runs ID Y0 Y1 [alpha_thr]: column runs of non-transparent pixels in a row band of build/s7g/orig/ID.png"""
import sys, numpy as np
from PIL import Image
a = np.asarray(Image.open('build/s7g/orig/%s.png' % sys.argv[1]).convert('RGBA'))
y0, y1 = int(sys.argv[2]), int(sys.argv[3]); thr = int(sys.argv[4]) if len(sys.argv) > 4 else 40
col = (a[y0:y1, :, 3] > thr).any(axis=0)
runs = []; s = None
for x, v in enumerate(list(col) + [False]):
    if v and s is None: s = x
    if not v and s is not None: runs.append((s, x - 1)); s = None
rows = (a[:, :, 3] > thr)
print('x-runs', runs)
for (s, e) in runs:
    r = np.nonzero(rows[y0:y1, s:e + 1].any(axis=1))[0]
    print((s, e), 'y', y0 + r.min(), y0 + r.max())
