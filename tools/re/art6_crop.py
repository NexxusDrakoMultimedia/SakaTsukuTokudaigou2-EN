import sys
from PIL import Image
# art6_crop.py in.png out.png x y w h scale
a = sys.argv
im = Image.open(a[1]).convert('RGBA')
bg = Image.new('RGBA', im.size, (90, 110, 90, 255)); bg.alpha_composite(im)
x, y, w, h, s = map(int, a[3:8])
bg.crop((x, y, x+w, y+h)).resize((w*s, h*s), Image.NEAREST).convert('RGB').save(a[2])
