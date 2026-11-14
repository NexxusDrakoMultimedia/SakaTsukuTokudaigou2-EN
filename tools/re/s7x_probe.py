import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, art7_lib as L
t = L.load('37285'); a = t['arr']
x0, y0 = 209, 289 + 32 * 1   # Strength chip cell
for y in range(y0, y0 + 30, 2):
    print(y - y0, [int(a[y, x, :3].mean()) for x in (x0 + 1, x0 + 2, x0 + 4, x0 + 98, x0 + 100, x0 + 102)])
