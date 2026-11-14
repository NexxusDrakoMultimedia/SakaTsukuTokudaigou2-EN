"""s7x_pal: decode bfgame.tbd#0/#1 with each guessed palette; write build/s7x/pal_<n>_<pvp>.png"""
import sys, os
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image
import pvr, pvr_scan, texinject
data = open('extracted/TRAINING/BFGAME.ZAR', 'rb').read()
got = []
sc = pvr_scan.Scanner(lambda t: got.append((t.path, t.payload)) if t.kind == 'PVP' else None, keep_rows=False)
sc.walk('TRAINING/BFGAME.ZAR', data)
for path, pl in got:
    print(path, len(pl))
    pal = pvr.parse_pvp(pl)
    print(' entries', len(pal.rgba), 'pix', pal.pix)
    for n in (0, 1):
        t = texinject.extract_pvr(data, 'bfgame.tbd#%d' % n)
        im = pvr.decode(t, palette=pal)
        nm = 'build/s7x/pal_%d_%s.png' % (n, os.path.basename(path))
        Image.fromarray(np.asarray(im).copy(), 'RGBA').save(nm)
        print(nm)
