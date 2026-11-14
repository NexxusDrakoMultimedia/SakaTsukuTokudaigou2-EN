"""s7g_cmp NAME [NAME...] [--scale 3]: before | re-encoded after over blue-grey (alpha respected) -> build/s7g/new/NAME.cmp.png"""
import sys, os
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
N = os.path.join(ROOT, 'build', 's7g', 'new')
args = sys.argv[1:]; sc = 3
if '--scale' in args:
    i = args.index('--scale'); sc = int(args[i + 1]); del args[i:i + 2]
def flat(p, bg):
    a = Image.open(p).convert('RGBA'); b = Image.new('RGBA', a.size, bg + (255,)); b.alpha_composite(a); return b.convert('RGB')
for n in args:
    ims = [flat(os.path.join(N, n + '.before.png'), (70, 70, 110)), flat(os.path.join(N, n + '.enc.png'), (70, 70, 110))]
    W = ims[0].width * 2 + 6
    c = Image.new('RGB', (W, ims[0].height), (0, 0, 0)); c.paste(ims[0], (0, 0)); c.paste(ims[1], (ims[0].width + 6, 0))
    c = c.resize((c.width * sc, c.height * sc), Image.NEAREST)
    c.save(os.path.join(N, n + '.cmp.png'))
