import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
import pvr, texinject
rec = int(sys.argv[1]); rows = [int(a) for a in sys.argv[2:]]
a = np.asarray(pvr.decode(texinject.extract_pvr('ETC_DATA/SS_TEX.ZAR', 'SS_PR1.TBD#%d' % rec)), int)
for y in rows:
    print(y, ' '.join('%d:%02x%02x%02x%s' % (x, *a[y, x, :3], '' if a[y, x, 3] > 200 else '*') for x in range(130, 256, 6)))
