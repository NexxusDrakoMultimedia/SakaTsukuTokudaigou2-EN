"""s7m_crop OUT.png SCALE x0 y0 x1 y1 src tid [installed]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import numpy as np
from PIL import Image
out, sc, x0, y0, x1, y1, src, tid = sys.argv[1:9]
sc, x0, y0, x1, y1 = map(int, (sc, x0, y0, x1, y1))
t = L.load(src, tid)
arrs = [t['arr']]
p = L.tex_path(src, tid)
if len(sys.argv) > 9 and os.path.exists(p):
    arrs.append(np.asarray(L.pvr.decode(open(p, 'rb').read())).copy())
ims = []
for a in arrs:
    im = Image.fromarray(a.astype(np.uint8), 'RGBA').crop((x0, y0, x1, y1))
    b = Image.new('RGBA', im.size, (255, 0, 255, 255)); b.alpha_composite(im); ims.append(b.convert('RGB'))
W = sum(i.width + 4 for i in ims); c = Image.new('RGB', (W, ims[0].height), (40, 40, 40)); x = 0
for i in ims: c.paste(i, (x, 0)); x += i.width + 4
c.resize((c.width * sc, c.height * sc), Image.NEAREST).save(out)
