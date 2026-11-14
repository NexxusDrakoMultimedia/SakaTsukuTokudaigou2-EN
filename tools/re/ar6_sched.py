"""ar6_sched: repaint the schedule cell words texture (GAME/ALLLOGOS.BIN [59], copy GAME/BINDLOGO.BIN [73], sweep id 10817):
rows OFF / ??? (Latin, kept) / 未定 -> TBD / 海外キャンプ -> Overseas Camp.   ar6_sched.py [--write]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import art7_lib as L, pvr, texinject

SRC, TID = 'GAME/ALLLOGOS.BIN', '[59]'
d = open(os.path.join(L.ROOT, 'extracted', *SRC.split('/')), 'rb').read()
pv = texinject.extract_pvr(d, TID)
t = dict(id='10817', src=SRC, tid=TID, pvr=pv, arr=np.asarray(pvr.decode(pv)).copy())
print('copies', L.dups(SRC, TID))
if '--boxes' in sys.argv:
    print(L.components(t['arr'], gx=6, gy=1)); sys.exit()
ITEMS = [
    dict(rect=(20, 66, 86, 30), text='TBD', font='arial-bold', erase={'mode': 'clear'}, pad=2, max_size=30),
    dict(rect=(0, 97, 128, 31), text='Overseas Camp', font='arial-narrow-bold', erase={'mode': 'clear'}, pad=1, max_size=28),
]
img = L.repaint(t, ITEMS)
res = L.repaint(t, ITEMS)
img = res[0] if isinstance(res, tuple) else res
print(type(res), [type(x).__name__ for x in res] if isinstance(res, tuple) else '')
png = os.path.join(L.ROOT, 'build', 'ar6', 'v', 'sched.png')
b = Image.new('RGBA', img.size, (90, 60, 120, 255)); b.alpha_composite(img.convert('RGBA'))
b.resize((384, 384), Image.NEAREST).convert('RGB').save(png)
if '--write' in sys.argv:
    new, w = L.encode_and_write(t, img.convert('RGBA'))
    for r in L.fit_report(new, t):
        print(r)
    print('wrote', w)
