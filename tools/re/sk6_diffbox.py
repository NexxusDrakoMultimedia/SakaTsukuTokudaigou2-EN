"""sk6_diffbox: bounding box of changed pixels between two pvr files. sk6_diffbox.py A.pvr B.pvr"""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr
a = np.asarray(pvr.decode(open(sys.argv[1], 'rb').read())).astype(int); b = np.asarray(pvr.decode(open(sys.argv[2], 'rb').read())).astype(int)
d = (a != b).any(-1); ys, xs = np.where(d)
print(sys.argv[1], 'changed px', int(d.sum()), 'bbox x%d..%d y%d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()) if d.any() else '')
