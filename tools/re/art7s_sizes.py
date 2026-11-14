import sys, glob, os
from PIL import Image
for f in sorted(glob.glob('build/art7/v/*_ba.png')):
    im = Image.open(f); print(os.path.basename(f)[:5], im.size, end=' | ')
