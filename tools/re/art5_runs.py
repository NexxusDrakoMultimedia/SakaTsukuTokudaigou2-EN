"""art5_runs IMG x0 x1 y0 y1 [thr] : alpha runs (rows then cols) inside window"""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGBA'))[:, :, 3]
x0, x1, y0, y1 = map(int, sys.argv[2:6])
thr = int(sys.argv[6]) if len(sys.argv) > 6 else 0
w = a[y0:y1, x0:x1] > thr
def runs(occ, off):
    r = []; s = None
    for i, v in enumerate(occ):
        if v and s is None: s = i
        if not v and s is not None: r.append((s + off, i - 1 + off)); s = None
    if s is not None: r.append((s + off, len(occ) - 1 + off))
    return r
print('rows', runs(w.any(1), y0))
print('cols', runs(w.any(0), x0))
