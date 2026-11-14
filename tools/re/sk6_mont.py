"""sk6_mont: montage of build/tex PNGs by id prefix. sk6_mont.py OUT.png ID [ID...]  (ids like 34688)"""
import os, sys, glob
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ims = []
for i in sys.argv[2:]:
    g = glob.glob(os.path.join(ROOT, 'build', 'tex', '*', i + '_*.png'))
    if not g: print('no', i); continue
    im = Image.open(g[0]).convert('RGBA'); b = Image.new('RGBA', im.size, (255, 0, 255, 255)); b.alpha_composite(im); ims.append(b.convert('RGB'))
W = sum(i.width for i in ims) + 4 * len(ims); H = max(i.height for i in ims)
o = Image.new('RGB', (W, H), (40, 0, 40)); x = 0
for i in ims: o.paste(i, (x, 0)); x += i.width + 4
o.save(sys.argv[1]); print(o.size)
