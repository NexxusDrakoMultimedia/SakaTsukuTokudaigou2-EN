import sys, glob, os
from PIL import Image
# usage: art6_view.py out.png scale id...  (composites decoded PNG on a mid-grey checker)
out = sys.argv[1]; sc = float(sys.argv[2]); ids = sys.argv[3:]
for i in ids:
    p = i if os.path.exists(i) else glob.glob('build/tex/*/%s_*.png' % i)[0]
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (90, 110, 90, 255))
    bg.alpha_composite(im)
    if sc != 1: bg = bg.resize((int(im.width*sc), int(im.height*sc)), Image.NEAREST)
    o = out if len(ids) == 1 else out.replace('.png', '_%s.png' % os.path.basename(p)[:5])
    bg.convert('RGB').save(o); print(o, p, im.size)
