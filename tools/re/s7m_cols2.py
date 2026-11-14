import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import numpy as np
t = L.load('FLOW_PRG/TWND1.ZAR', 'selb.tbd#0'); a = t['arr']
for y in (10, 42, 74, 106, 138, 170, 202, 234):
    print(y, [tuple(a[y, x]) for x in range(91, 99)])
# per-column alpha count x 88..100 over the whole sheet
print([int((a[:, x, 3] > 0).sum()) for x in range(86, 102)])
