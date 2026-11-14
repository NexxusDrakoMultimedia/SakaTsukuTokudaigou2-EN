"""ar6_bansheet: before|after sheets of the repainted banners: ar6_bansheet.py OUTPREFIX [per_sheet] (uses build/ar6/ban/*.png)"""
import os, sys, glob
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
pre = sys.argv[1]; per = int(sys.argv[2]) if len(sys.argv) > 2 else 20
ids = sorted(os.path.basename(p)[:5] for p in glob.glob(os.path.join(ROOT, 'build', 'ar6', 'ban', '*.png')))
def orig(i):
    return glob.glob(os.path.join(ROOT, 'build', 'tex', 'EVENT__*', i + '_*.png'))[0]
for n in range(0, len(ids), per):
    ch = ids[n:n + per]
    cols = 2
    rows = (len(ch) + cols - 1) // cols
    o = Image.new('RGB', (cols * 520, rows * 38), (70, 70, 90))
    d = ImageDraw.Draw(o)
    for k, i in enumerate(ch):
        x = (k % cols) * 520; y = (k // cols) * 38
        for j, p in enumerate((orig(i), os.path.join(ROOT, 'build', 'ar6', 'ban', i + '.png'))):
            im = Image.open(p).convert('RGBA'); b = Image.new('RGBA', im.size, (70, 70, 90, 255)); b.alpha_composite(im)
            o.paste(b.convert('RGB'), (x + j * 258, y + 3))
    fn = '%s_%02d.png' % (pre, n // per); o.save(fn); print(fn)
