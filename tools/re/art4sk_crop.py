"""art4sk_crop FILEREL x y w h scale -> before|after crop of installed pvr vs original, stacked, build/art4sk/crop.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
from PIL import Image
import pvr, texinject
rel = sys.argv[1]; x, y, w, h, s = map(int, sys.argv[2:7])
f, t = rel.rsplit('/', 1); t = t[:-4]
new = open(os.path.join(ROOT, 'translation', 'textures', *rel.split('/')), 'rb').read()
old = texinject.extract_pvr(f, t)
def dec(b): return Image.fromarray(np.asarray(pvr.decode(b), np.uint8), 'RGBA')
ims = []
for b in (old, new):
    im = dec(b).crop((x, y, x + w, y + h))
    bg = Image.new('RGBA', im.size, (60, 60, 60, 255)); bg.alpha_composite(im)
    ims.append(bg.resize((w * s, h * s), Image.NEAREST))
sh = Image.new('RGB', (w * s, h * s * 2 + 6), (255, 0, 255))
sh.paste(ims[0].convert('RGB'), (0, 0)); sh.paste(ims[1].convert('RGB'), (0, h * s + 6))
sh.save(os.path.join(ROOT, 'build', 'art4sk', 'crop.png'))
