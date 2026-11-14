"""s7m_jini [--write]: Office personnel submenu plates 07009 07012 07015 07018 07021 (ALLJINI.ZAR jini*.tbd#1, 128x32 RGB565)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import numpy as np


def plate_fill(a, x0=6, y0=5, w=117, h=23, tol=6):
    for y in range(y0, y0 + h):
        seg = a[y, x0:x0 + w, :3].astype(int)
        lum = seg[:, 0] * 0.299 + seg[:, 1] * 0.587 + seg[:, 2] * 0.114
        ok = (lum > 205) & (seg[:, 2] > 215)
        if ok.sum() < 6:
            continue
        bg = np.median(seg[ok], axis=0).astype(int)
        bad = np.abs(seg - bg).max(-1) > tol
        a[y, x0:x0 + w][bad, :3] = bg



JOBS = [('jini11.tbd#1', '07009', 'Sign Players'), ('jini7.tbd#1', '07012', 'Transfer'), ('jini10.tbd#1', '07015', 'Study Abroad'),
        ('jini8.tbd#1', '07018', 'Change Manager'), ('jini9.tbd#1', '07021', 'Change Scout')]
ERASE = {'mode': 'mask', 'ink': [{'luma_lt': 150}], 'dilate': 1, 'fill': 'hfill'}
STYLES = {'k': {'font': ['arial-narrow-bold', 'arial-bold'], 'fill': '#000000'}}
SRC = 'FLOW_PRG/ALLJINI.ZAR'
write = '--write' in sys.argv
for tid, sid, text in JOBS:
    t = L.load(SRC, tid)
    reg = [{'id': 'r', 'text': text, 'x': 8, 'y': 6, 'w': 112, 'h': 21, 'style': 'k', 'size': 17, 'min_sx': 0.8,
            'align': 'center', 'valign': 'middle', 'pad': 0,
            'erase': None}]
    pre = [plate_fill]
    out, rep = L.render(t, reg, STYLES, 'rgb565', pre=pre)
    for w in rep['warnings']:
        print(sid, 'WARN', w)
    L.sheet(t['arr'], out, os.path.join(L.OUT, sid + '_ba.png'), 4)
    if write:
        new, paths, bad = L.write(t, out)
        print(sid, 'wrote', len(paths), 'bad', bad)
    else:
        print(sid, 'ok', rep.get('regions', '')[:1] if isinstance(rep, dict) else '')
