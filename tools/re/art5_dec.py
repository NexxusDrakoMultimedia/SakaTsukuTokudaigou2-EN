"""art5_dec - decode extra textures: art5_dec.py FILE TID OUT.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T, pvr
f, tid, out = sys.argv[1:4]
src = open(os.path.join(ROOT, 'extracted', *f.split('/')), 'rb').read()
p = T.extract_pvr(src, tid)
open(out[:-4] + '.pvr', 'wb').write(p)
pvr.to_png(pvr.decode(p), out)
