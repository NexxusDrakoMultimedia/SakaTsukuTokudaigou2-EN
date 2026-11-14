"""art4sk_col FILEREL which(old|new) x0 x1 y0 y1 : dump rgba hex"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
import pvr, texinject
rel, which = sys.argv[1:3]; x0, x1, y0, y1 = map(int, sys.argv[3:7])
f, t = rel.rsplit('/', 1); t = t[:-4]
b = texinject.extract_pvr(f, t) if which == 'old' else open(os.path.join(ROOT, 'translation', 'textures', *rel.split('/')), 'rb').read()
a = np.asarray(pvr.decode(b), int)
for y in range(y0, y1):
    print(y, ' '.join('%02x%02x%02x%02x' % tuple(a[y, x]) for x in range(x0, x1)))
