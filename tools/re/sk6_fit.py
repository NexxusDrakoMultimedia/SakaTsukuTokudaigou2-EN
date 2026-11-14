"""sk6_fit: skeptic check, try every .pvr under translation/textures/GAME/<file> with policy exact; list failures.
Usage: sk6_fit.py GAME/ALLLOGOS.BIN [...]"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject
for f in sys.argv[1:]:
    d = os.path.join(ROOT, 'translation', 'textures', *f.split('/'))
    src = open(os.path.join(ROOT, 'extracted', *f.split('/')), 'rb').read()
    ok = bad = 0
    for n in sorted(os.listdir(d)):
        if not n.endswith('.pvr'):
            continue
        tid = n[:-4]
        pv = open(os.path.join(d, n), 'rb').read()
        try:
            texinject.replace_texture(f, tid, pv, policy='exact')
            ok += 1
        except Exception as e:
            bad += 1
            print('FAIL', f, tid, type(e).__name__, str(e)[:150])
    print(f, 'ok', ok, 'bad', bad)
