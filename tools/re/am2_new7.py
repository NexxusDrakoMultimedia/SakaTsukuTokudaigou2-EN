"""am2_new7 - crop before|after for art7 id from build/am2/o7_ID.png and build/art7/out/ID.png: ID x y w h scale OUT"""
import sys
from PIL import Image
i, x, y, w, h, sc, out = sys.argv[1:8]
x, y, w, h, sc = map(int, (x, y, w, h, sc))
a = Image.open('build/am2/o7_%s.png' % i).convert('RGBA').crop((x, y, x + w, y + h))
b = Image.open('build/art7/out/%s.png' % i).convert('RGBA').crop((x, y, x + w, y + h))
s = Image.new('RGBA', (w * sc * 2 + 6, h * sc), (255, 0, 255, 255))
for k, im in enumerate((a, b)):
    bg = Image.new('RGBA', im.size, (90, 90, 90, 255)); bg.alpha_composite(im)
    s.paste(bg.resize((w * sc, h * sc), Image.NEAREST), (k * (w * sc + 6), 0))
s.save(out)
