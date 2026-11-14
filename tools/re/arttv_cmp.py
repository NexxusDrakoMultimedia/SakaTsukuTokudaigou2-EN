import sys
from PIL import Image
# usage: S out id:x0:y0:x1:y1 ...   before over after stacked
S = int(sys.argv[1]); out = sys.argv[2]
import glob
tiles = []
for spec in sys.argv[3:]:
    t, x0, y0, x1, y1 = spec.split(':'); box = tuple(map(int, (x0, y0, x1, y1)))
    a = Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/%s_*.png' % t)[0]).convert('RGBA').crop(box)
    b = Image.open('build/art_tv/%s.dec.png' % t).convert('RGBA').crop(box)
    tiles.append((a, b))
w = max(a.width for a, b in tiles) * 2 + 4
h = sum(a.height + 4 for a, b in tiles)
m = Image.new('RGB', (w, h), (100, 100, 100))
y = 0
for a, b in tiles:
    for i, im in enumerate((a, b)):
        bg = Image.new('RGBA', im.size, (100, 100, 100, 255)); bg.alpha_composite(im)
        m.paste(bg.convert('RGB'), (i * (a.width + 4), y))
    y += a.height + 4
m.resize((m.width * S, m.height * S), Image.NEAREST).save(out)
