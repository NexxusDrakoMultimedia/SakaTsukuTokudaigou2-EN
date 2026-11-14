"""s7x_view: side-by-side viewer.  s7x_view.py OUT.png SCALE X,Y,W,H A.png|A.pvr [B ...]   (stacked horizontally, composited on grey/magenta)"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, 'tools')
import pvr
out, sc, crop = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ims = []
for p in sys.argv[4:]:
    if p.endswith('.pvr'):
        im = Image.fromarray(np.asarray(pvr.decode(open(p, 'rb').read())).copy(), 'RGBA')
    else:
        im = Image.open(p).convert('RGBA')
    if crop != '0':
        x, y, w, h = [int(v) for v in crop.split(',')]
        im = im.crop((x, y, x + w, y + h))
    bg = Image.new('RGBA', im.size, (110, 70, 110, 255)); bg.alpha_composite(im)
    ims.append(bg.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST))
W = sum(i.width for i in ims) + 6 * (len(ims) - 1); H = max(i.height for i in ims)
o = Image.new('RGB', (W, H), (255, 255, 255)); x = 0
for i in ims:
    o.paste(i, (x, 0)); x += i.width + 6
o.save(out); print(out, o.size)
