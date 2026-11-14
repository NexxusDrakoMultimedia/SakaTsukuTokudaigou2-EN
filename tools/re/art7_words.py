"""art7_words ID x y w h [gap] [thr]: split the ink inside a strip into words (column runs separated by >= gap empty
columns) and print each word's tight box (x, y, w, h)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import art7_lib as L

a = sys.argv[1:]
id5 = a[0]
x, y, w, h = [int(v) for v in a[1:5]]
gap = int(a[5]) if len(a) > 5 else 4
thr = int(a[6]) if len(a) > 6 else 100
arr = L.load(id5)['arr']
ink = arr[y:y + h, x:x + w, 3] > thr
cols = ink.any(0)
runs = []
start = None
last = None
for i, c in enumerate(cols):
    if c:
        if start is None:
            start = i
        last = i
    elif start is not None and i - last >= gap:
        runs.append((start, last))
        start = None
if start is not None:
    runs.append((start, last))
for s, e in runs:
    sub = ink[:, s:e + 1]
    rows = np.nonzero(sub.any(1))[0]
    print((x + s, y + int(rows.min()), e - s + 1, int(rows.max() - rows.min() + 1)))
