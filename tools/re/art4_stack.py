import sys
from PIL import Image
# art4_stack.py out.png scale cols [crop=x,y,w,h] file...  : composites on checker, grid of images
out, scale, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rest = sys.argv[4:]
crop = None
if rest and rest[0].startswith('crop='):
    crop = tuple(int(v) for v in rest[0][5:].split(','))
    rest = rest[1:]
ims = []
for p in rest:
    im = Image.open(p).convert('RGBA')
    if crop:
        x, y, w, h = crop
        im = im.crop((x, y, x + w, y + h))
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
