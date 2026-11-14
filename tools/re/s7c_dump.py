"""s7c_dump: montage of the 15 STAFFLST role-title textures (originals), 2 columns x scale; prints ink boxes."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pvr, texinject  # noqa
MEMBERS = ['t_direc', 't_tdirec', 't_plan', 't_prog', 't_npro', 't_design', 't_stdirec', 't_kai', 't_jikkyo', 't_promo', 't_pub', 't_special', 't_assip', 't_produ', 't_gene']
SRC = 'GAME/STAFFLST.ZAR'

def load(m):
    with open(os.path.join(ROOT, 'extracted', 'GAME', 'STAFFLST.ZAR'), 'rb') as f:
        d = f.read()
    pv = texinject.extract_pvr(d, m + '.pvr')
    return pv, np.asarray(pvr.decode(pv)).copy()

if __name__ == '__main__':
    out = sys.argv[1]
    ms = sys.argv[2:] or MEMBERS
    tiles = []
    for m in ms:
        pv, a = load(m)
        ys, xs = np.nonzero(a[..., 3] > 40)
        print(m, a.shape, 'ink bbox', xs.min(), ys.min(), xs.max(), ys.max())
        im = Image.fromarray(a.astype(np.uint8), 'RGBA')
        bg = Image.new('RGBA', im.size, (90, 90, 110, 255)); bg.alpha_composite(im)
        tiles.append(bg.convert('RGB'))
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    c = Image.new('RGB', (cols * 132, rows * 132), (40, 0, 40))
    for i, t in enumerate(tiles):
        c.paste(t, ((i % cols) * 132, (i // cols) * 132))
    c.save(out); print(out, c.size)
