"""art5_fit - slot check of every group-5 texture copy against the original files. art5_fit.py [ids...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
T = L.texinject
ids = sys.argv[1:] or [i for i in L.MAN if os.path.exists(os.path.join(L.ART, 'new', i + '.png'))]
bad = 0
for i in ids:
    f, tid = L.MAN[i]['copies'][0]
    src = open(os.path.join(L.ROOT, 'extracted', *f.split('/')), 'rb').read()
    p = open(os.path.join(L.TEXDIR, *f.split('/'), tid + '.pvr'), 'rb').read()
    try:
        r = T.fit_check(src, tid, p)
        print(i, f, tid, r)
    except Exception as e:
        bad += 1
        print(i, f, tid, 'ERR', e)
print('bad', bad)
