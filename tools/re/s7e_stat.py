"""s7e_stat ID: alpha/colour stats of a texture"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import art7_lib as L
t = L.load(sys.argv[1])
a = t['arr']
print(a.shape, t['info'].get('format'))
al = a[..., 3]
print('alpha hist', np.bincount(al.ravel() >> 4, minlength=16))
op = al > 8
print('rgb of opaque: min', a[op][:, :3].min(0), 'max', a[op][:, :3].max(0))
ys, xs = np.nonzero(op)
print('bbox', xs.min(), ys.min(), xs.max(), ys.max())
