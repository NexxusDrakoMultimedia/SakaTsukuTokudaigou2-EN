import sys, os, glob
from PIL import Image
# usage: art4_sheet.py out.png scale cols id1 id2 ...  (ids are prefixes in build/tex/*/)
out, scale, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ims = []
for i in sys.argv[4:]:
    p = glob.glob('build/tex/*/%s_*.png' % i)[0]
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (90, 90, 90, 255))
    for y in range(0, im.size[1], 8):
        for x in range(0, im.size[0], 8):
            if (x // 8 + y // 8) % 2:
                bg.paste((120, 120, 120, 255), (x, y, x + 8, y + 8))
    bg.alpha_composite(im)
    ims.append(bg.convert('RGB').resize((im.size[0] * scale, im.size[1] * scale), Image.NEAREST))
W = max(i.size[0] for i in ims); H = max(i.size[1] for i in ims)
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (cols * (W + 6), rows * (H + 6)), (0, 0, 60))
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * (W + 6), (k // cols) * (H + 6)))
S.save(out)
