"""s7m_pvrpng OUT.png [--scale N] FILE.pvr ... : decode local .pvr files side by side on magenta."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr  # noqa

args = sys.argv[1:]
scale = 1
if '--scale' in args:
    i = args.index('--scale'); scale = int(args[i + 1]); del args[i:i + 2]
out = args[0]
ims = []
for p in args[1:]:
    with open(p, 'rb') as f:
        a = np.asarray(pvr.decode(f.read())).copy()
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    b = Image.new('RGBA', im.size, (255, 0, 255, 255)); b.alpha_composite(im)
    ims.append(b.convert('RGB'))
W = sum(i.width for i in ims) + 4 * (len(ims) - 1); H = max(i.height for i in ims)
c = Image.new('RGB', (W, H), (60, 0, 60)); x = 0
for i in ims:
    c.paste(i, (x, 0)); x += i.width + 4
c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
c.save(out); print(out, c.size)
