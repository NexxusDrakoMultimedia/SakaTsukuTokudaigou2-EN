"""s7x_inkcheck2: left-strip ink extents (installed vs original) of texture 37285 rows 194-350"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L, pvr
t = L.load('37285')
o = t['arr']
n = np.asarray(pvr.decode(open(L.tex_path(t['src'], t['tid']), 'rb').read()))
for name, a in (('orig', o), ('inst', n)):
    for (y0, y1, lab) in ((194, 223, 'Practice Orders'), (227, 256, 'Change Policy'), (259, 287, 'Run Practice'), (290, 319, 'View Teamwork'), (323, 350, 'Team Check')):
        m = (a[y0:y1, 0:100, :3].astype(int).sum(axis=2) > 600)
        c = np.where(m.any(axis=0))[0]
        print(name, lab, (int(c.min()), int(c.max())) if len(c) else None)
