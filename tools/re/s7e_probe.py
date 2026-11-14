"""s7e_probe: scratch pixel dump: s7e_probe.py ID x0 y0 w h"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import art7_lib as L
t = L.load(sys.argv[1])
a = t['arr']
x0, y0, w, h = [int(v) for v in sys.argv[2:6]]
for y in range(y0, y0 + h):
    print(y, ' '.join('%02x%02x%02x' % tuple(int(v) >> 4 << 4 >> 4 for v in a[y, x, :3]) if False else '%x%x%x' % tuple(int(v) >> 4 for v in a[y, x, :3]) for x in range(x0, x0 + w)))
