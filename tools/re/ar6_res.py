"""ar6_res: ar6_res.py id5 [id5...] -> source, texinject id, copies, and writes build/ar6/v/res_<id>.png (decoded)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art7_lib as L
from PIL import Image
for i in sys.argv[1:]:
    try:
        src, tid, d = L.resolve(i)
    except Exception as e:
        print(i, 'ERR', e); continue
    print(i, src, tid, L.dups(src, tid))
    t = L.load(i)
    Image.fromarray(t['arr'], 'RGBA').save(os.path.join(HERE, '..', '..', 'build', 'ar6', 'v', 'res_%s.png' % i))
