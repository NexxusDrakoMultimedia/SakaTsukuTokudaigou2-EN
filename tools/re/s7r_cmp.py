"""s7r_cmp ID PNG : compare the INSTALLED texture (decoded) with a PNG; print changed-pixel count and bbox"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import art7_lib as L, pvr
t = L.load(sys.argv[1])
p = L.tex_path(t['src'], t['tid'])
cur = pvr.decode(open(p, 'rb').read())
png = np.asarray(Image.open(sys.argv[2]).convert('RGBA'))
d = (cur != png).any(-1)
print('installed', p, 'differs', int(d.sum()))
if d.any():
    ys, xs = np.nonzero(d); print('bbox', xs.min(), ys.min(), xs.max(), ys.max())
