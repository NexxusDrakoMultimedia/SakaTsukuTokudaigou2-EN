import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
import pvr
rec, x0, x1, y0, y1 = map(int, sys.argv[1:6])
b = open(os.path.join(ROOT, 'translation', 'textures', 'ETC_DATA', 'SS_TEX.ZAR', 'SS_PR1.TBD#%d.pvr' % rec), 'rb').read()
a = np.asarray(pvr.decode(b), int)
for y in range(y0, y1):
    print(y, ' '.join('%02x%02x%02x%02x' % tuple(a[y, x]) for x in range(x0, x1)))
