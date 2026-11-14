"""s7p_fit - for every plate texture: packed size needed by the written .pvr vs the slot in the original container.
usage: s7p_fit.py [--all]   (default: only those that do not fit)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject
allp = '--all' in sys.argv
tot = bad = 0
for f in ('ALLLOGOS.BIN', 'BINDLOGO.BIN', 'BINDNAME.BIN'):
    d = os.path.join(ROOT, 'translation', 'textures', 'GAME', f)
    src = open(os.path.join(ROOT, 'extracted', 'GAME', f), 'rb').read()
    for fn in sorted(os.listdir(d), key=lambda s: int(s[1:-5])):
        tid = fn[:-4]
        r = texinject.fit_check(src, tid, open(os.path.join(d, fn), 'rb').read())
        tot += 1
        if not r['fits']:
            bad += 1
        if allp or not r['fits']:
            print(f, tid, r)
print('total', tot, 'not fitting', bad)
