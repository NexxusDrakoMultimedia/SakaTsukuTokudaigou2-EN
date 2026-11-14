"""s7c_mont OUT.png : stack the build/s7c/v/*_ba.png before/after panels (2 columns)."""
import os, sys, glob
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
fs = sorted(glob.glob(os.path.join(ROOT, 'build', 's7c', 'v', '*_ba.png')))
ims = [Image.open(f) for f in fs]
w, h = ims[0].size
c = Image.new('RGB', (w * 2 + 8, (len(ims) + 1) // 2 * (h + 4)), (40, 0, 40))
for i, im in enumerate(ims):
    c.paste(im, ((i % 2) * (w + 8), (i // 2) * (h + 4)))
c.save(sys.argv[1]); print(len(ims), c.size)
