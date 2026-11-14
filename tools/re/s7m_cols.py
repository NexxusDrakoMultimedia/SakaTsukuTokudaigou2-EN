"""s7m_cols SRC TID Y0 Y1 : x runs of opaque pixels (alpha>40) in rows Y0..Y1 (gaps >= 3 split runs)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import s7m_lib as L
t = L.load(sys.argv[1], sys.argv[2]); a = t['arr']
y0, y1 = int(sys.argv[3]), int(sys.argv[4])
col = (a[y0:y1 + 1, :, 3] > 40).any(0)
x = 0; runs = []
while x < len(col):
    if col[x]:
        s = x; gap = 0
        while x < len(col) and (col[x] or gap < 3):
            gap = 0 if col[x] else gap + 1
            x += 1
        runs.append((s, x - gap - 1))
    x += 1
print(runs)
