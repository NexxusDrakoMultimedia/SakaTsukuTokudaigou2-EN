"""art5_rows: alpha row runs inside a column window. art5_rows.py IMG x0 x1 [thr]"""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGBA'))[:, :, 3]
x0, x1 = int(sys.argv[2]), int(sys.argv[3])
thr = int(sys.argv[4]) if len(sys.argv) > 4 else 0
occ = (a[:, x0:x1] > thr).any(1)
runs = []; s = None
for y, v in enumerate(occ):
    if v and s is None: s = y
    if not v and s is not None: runs.append((s, y - 1)); s = None
if s is not None: runs.append((s, len(occ) - 1))
print(runs)
