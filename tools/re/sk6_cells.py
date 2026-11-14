"""sk6_cells: ink columns (white-ish, alpha>128) in BAR rows 30..70 for old / ar6-start / installed, per 4-px-gap group."""
import os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, ar5_dump
old = ar5_dump.get('ETC_DATA/BAR.TBD', '#0')
now = np.asarray(pvr.decode(open(os.path.join(ROOT, 'translation/textures/ETC_DATA/BAR.TBD/#0.pvr'), 'rb').read()))
prv = np.asarray(pvr.decode(open(os.path.join(ROOT, 'build/ar6/texbak/ETC_DATA/BAR.TBD/#0.pvr'), 'rb').read()))
for nm, im in (('old', old), ('prev', prv), ('now', now)):
    sub = im[30:70, 150:400]
    m = (sub[..., 3] > 128) & (sub[..., :3].min(-1) > 190)
    cols = np.where(m.any(0))[0] + 150
    groups = []; s = cols[0]; p = cols[0]
    for c in cols[1:]:
        if c - p > 3: groups.append((s, p)); s = c
        p = c
    groups.append((s, p))
    rows = np.where(m.any(1))[0] + 30
    print(nm, groups, 'rows', rows[0], rows[-1])
