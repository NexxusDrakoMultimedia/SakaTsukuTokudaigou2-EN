"""art5_cols: alpha column runs. art5_cols.py IMG [thr]"""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGBA'))[:, :, 3]
thr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
occ = (a > thr).any(0)
runs = []
s = None
for x, v in enumerate(occ):
    if v and s is None:
        s = x
    if not v and s is not None:
        runs.append((s, x - 1)); s = None
if s is not None:
    runs.append((s, len(occ) - 1))
print(runs)
rows = (a > thr).any(1)
ys = np.where(rows)[0]
print('rows', ys.min(), ys.max())
