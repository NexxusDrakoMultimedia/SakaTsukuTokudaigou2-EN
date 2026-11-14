"""art1sk_fix04112 - clean base for 04112: erase the kanji ink and refill with marble borrowed from the strip, then re-run the spec."""
import os, sys, json, colorsys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
B = os.path.join(ROOT, 'build', 'art1')
a = np.asarray(Image.open(os.path.join(B, 'orig', '04112.png')).convert('RGBA')).copy()
H, W = a.shape[:2]
rgb = a[..., :3].astype(float)
mx = rgb.max(2); mn = rgb.min(2)
sat = (mx - mn) / np.maximum(mx, 1)
luma = rgb @ [0.299, 0.587, 0.114]
ink = (sat < 0.22) & (luma > 40) & (a[..., 3] > 0)
box = np.zeros((H, W), bool); box[203:249, 143:238] = True
ink &= box
# grow 2px (square) but never into the yellow border
m = ink.copy()
for _ in range(2):
    p = np.pad(m, 1)
    m = sum(p[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) > 0
yellow = (rgb[..., 0] > 100) & (rgb[..., 1] > 100) & (rgb[..., 2] < 0.7 * rgb[..., 1]) & (sat > 0.3)
m &= box & ~yellow & (a[..., 3] > 0)
out = a.copy()
ys, xs = np.nonzero(m)
for y, x in zip(ys, xs):
    yy = (231 - y)  # reflect rows above 228 into the strip body 228..247
    if yy < 0:
        yy = 0
    per = 28
    r = yy % per
    yr = 231 + (r if r < 14 else per - 1 - r)
    yr = min(yr, 244)
    band = yy // 14
    xr = 34 + ((x * 3 + band * 41) % 76)
    if y >= 231:
        yr = y
        xr = 34 + ((x - 143) % 76)
    out[y, x] = a[yr, xr]
Image.fromarray(out, 'RGBA').save(os.path.join(ROOT, 'build', 'art1sk', '04112_clean.png'))
print('masked', int(m.sum()))
