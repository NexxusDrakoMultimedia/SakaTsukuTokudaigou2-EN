"""ar6_bandump: print per-column stats of banner textures: ar6_bandump.py ID ... (leftmost opaque x, rightmost, rows)"""
import os, sys, glob
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for i in sys.argv[1:]:
    p = glob.glob(os.path.join(ROOT, 'build', 'tex', 'EVENT__*', i + '_*.png'))[0]
    a = np.asarray(Image.open(p).convert('RGBA')).astype(int)
    op = a[..., 3] > 128
    cols = np.nonzero(op.any(0))[0]
    rows = np.nonzero(op.any(1))[0]
    print(i, p.split(os.sep)[-2], 'x', cols.min(), cols.max(), 'y', rows.min(), rows.max())
    for y in range(rows.min(), rows.max() + 1, 3):
        xs = np.nonzero(op[y])[0]
        print('  y%2d first=%3d  px@first+2..: %s  px@250=%s' % (y, xs.min(), a[y, xs.min() + 2, :4].tolist(), a[y, 250, :4].tolist()))
