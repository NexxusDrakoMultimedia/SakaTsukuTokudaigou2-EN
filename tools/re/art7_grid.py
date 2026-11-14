"""art7_grid ID OUT.png [x y w h [scale]]: crop of a decoded texture (or 'ID' + 'o' for repainted) with a pixel grid (every 16 px,
labelled every 32 px in texture coordinates).  Default whole texture at 2x (1x if wider than 512)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw
import art7_lib as L


def main():
    ident, out = sys.argv[1], sys.argv[2]
    a = [int(v) for v in sys.argv[3:]]
    if ident.endswith('o'):
        arr = np.asarray(Image.open(os.path.join(L.OUT, 'out', ident[:-1] + '.png')).convert('RGBA'))
    else:
        arr = L.load(ident)['arr']
    H, W = arr.shape[:2]
    x, y, w, h = (a + [0, 0, W, H][len(a):])[:4] if len(a) < 4 else a[:4]
    sc = a[4] if len(a) > 4 else (2 if w <= 512 else 1)
    im = Image.fromarray(arr[y:y + h, x:x + w].astype(np.uint8), 'RGBA')
    bg = Image.new('RGBA', im.size, (110, 110, 130, 255))
    bg.alpha_composite(im)
    bg = bg.resize((w * sc, h * sc), Image.NEAREST).convert('RGB')
    d = ImageDraw.Draw(bg)
    for gx in range((x + 15) // 16 * 16, x + w, 16):
        px = (gx - x) * sc
        d.line([px, 0, px, h * sc], fill=(255, 255, 255) if gx % 32 == 0 else (90, 90, 110), width=1)
        if gx % 32 == 0:
            d.text((px + 1, 1), str(gx), fill=(255, 255, 0))
    for gy in range((y + 15) // 16 * 16, y + h, 16):
        py = (gy - y) * sc
        d.line([0, py, w * sc, py], fill=(255, 255, 255) if gy % 32 == 0 else (90, 90, 110), width=1)
        if gy % 32 == 0:
            d.text((1, py + 1), str(gy), fill=(0, 255, 255))
    bg.save(out)


main()
