"""ar6_ext: ar6_ext.py SRC TID OUT.png  -> decoded texture (flattened on magenta) and its info; extracted/ is read-only."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr, texinject
src, tid, out = sys.argv[1:4]
d = open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb').read()
a = np.asarray(pvr.decode(texinject.extract_pvr(d, tid))).copy()
im = Image.fromarray(a, 'RGBA')
b = Image.new('RGBA', im.size, (90, 60, 120, 255)); b.alpha_composite(im)
b = b.resize((im.width * 3, im.height * 3), Image.NEAREST)
b.convert('RGB').save(out)
print(a.shape)
