"""s7c_verify OUT.png : decode the installed translation/textures/GAME/STAFFLST.ZAR/*.pvr.pvr files, check they parse, size and
that ink stays inside the cell, and write a before/after montage (original left, installed right) to OUT.png."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7c_dump as D
import pvr
ROOT = D.ROOT
TD = os.path.join(ROOT, 'translation', 'textures', 'GAME', 'STAFFLST.ZAR')
tiles = []
for m in D.MEMBERS:
    p = os.path.join(TD, m + '.pvr.pvr')
    raw = open(p, 'rb').read()
    new = np.asarray(pvr.decode(raw)).copy()
    pv, old = D.load(m)
    assert new.shape == old.shape, (m, new.shape, old.shape)
    ys, xs = np.nonzero(new[..., 3] > 40)
    print(m, len(raw), new.shape, 'ink', xs.min(), ys.min(), xs.max(), ys.max())
    t = Image.new('RGB', (264, 132), (40, 0, 40))
    for k, a in enumerate((old, new)):
        im = Image.fromarray(a.astype(np.uint8), 'RGBA')
        bg = Image.new('RGBA', im.size, (90, 90, 110, 255)); bg.alpha_composite(im)
        t.paste(bg.convert('RGB').crop((0, 0, 128, 128)), (k * 136, 0))
    tiles.append(t)
cols = 2
rows = (len(tiles) + 1) // 2
c = Image.new('RGB', (cols * 268, rows * 134), (40, 0, 40))
for i, t in enumerate(tiles):
    c.paste(t, ((i % cols) * 268, (i // cols) * 134))
c = c.resize((c.width * 2, c.height * 2), Image.NEAREST)
c.save(sys.argv[1]); print(c.size)
