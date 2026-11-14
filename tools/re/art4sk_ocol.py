import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
import pvr, texinject
rec = int(sys.argv[1]); xs = [int(a) for a in sys.argv[2:]]
a = np.asarray(pvr.decode(texinject.extract_pvr('ETC_DATA/SS_TEX.ZAR', 'SS_PR1.TBD#%d' % rec)), int)
for y in range(3, 36):
    print(y, ' '.join('%d:%02x%02x%02x' % (x, *a[y, x, :3]) for x in xs))
