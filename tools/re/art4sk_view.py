"""art4sk_view - skeptic: decode installed group-4 PVRs vs the originals, write before|after sheets to build/art4sk/."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np
from PIL import Image
import pvr, texinject
TD = os.path.join(ROOT, 'translation', 'textures')
OUT = os.path.join(ROOT, 'build', 'art4sk')
os.makedirs(OUT, exist_ok=True)
FILES = [l.strip() for l in open(os.path.join(HERE, 'art4sk_list.txt'), encoding='utf8') if l.strip()]
def dec(b):
    return Image.fromarray(np.asarray(pvr.decode(b), np.uint8), 'RGBA')
def bg(im, c=(60, 60, 60)):
    b = Image.new('RGBA', im.size, c + (255,)); b.alpha_composite(im); return b
for rel in FILES:
    f, t = rel.rsplit('/', 1)
    t = t[:-4]
    new = open(os.path.join(TD, *rel.split('/')), 'rb').read()
    old = texinject.extract_pvr(f, t)
    a, b = dec(old), dec(new)
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    W, H = a.size
    if W * s > 1000: s = 1
    sheet = Image.new('RGBA', (W * s * 2 + 8, H * s), (255, 0, 255, 255))
    sheet.paste(bg(a).resize((W * s, H * s), Image.NEAREST), (0, 0))
    sheet.paste(bg(b).resize((W * s, H * s), Image.NEAREST), (W * s + 8, 0))
    name = rel.replace('/', '_').replace('#', 'n')[:-4] + '.png'
    sheet.convert('RGB').save(os.path.join(OUT, name))
    print(name, a.size, len(old), len(new))
