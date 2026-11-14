"""sk6_fit2: combined replace_textures on a whole container with exact policy. sk6_fit2.py GAME/ALLLOGOS.BIN"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject
for f in sys.argv[1:]:
    d = os.path.join(ROOT, 'translation', 'textures', *f.split('/'))
    m = {n[:-4]: open(os.path.join(d, n), 'rb').read() for n in os.listdir(d) if n.endswith('.pvr')}
    try:
        r = texinject.replace_textures(f, m, policy='exact')
        print(f, 'combined OK', len(m))
    except Exception as e:
        print(f, 'combined FAIL', type(e).__name__, str(e)[:300])
