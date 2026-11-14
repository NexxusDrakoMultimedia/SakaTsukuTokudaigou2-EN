import csv, os, sys
import numpy as np
from PIL import Image
S = os.environ.get('SAKATSUKU_SCRATCH', os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')), 'build', 'scratch')) + '/'
im = Image.open(S + 'images/51.webp').convert('RGB')
k = 640 / 984
box = (75, 378, 196, 421)
crop = im.crop(box)
w, h = crop.size
def mk(scale):
    c = crop.resize((max(8, int(w * k * scale)), max(8, int(h * k * scale))), Image.LANCZOS)
    a = np.asarray(c).astype(np.float32)
    m = (a.min(axis=2) > 185).astype(np.float32)
    return m
tmpls = {s: mk(s) for s in (1.0, 1.5, 2.0, 0.75)}
for s, t in tmpls.items(): print(s, t.shape, t.sum())
rows = list(csv.reader(open('build/tex/index.tsv', encoding='utf-8'), delimiter='\t'))
res = []
for r in rows[1:]:
    if not r[12]: continue
    p = os.path.join('build/tex', r[1].replace('/', '__'), r[0] + '.png')
    if not os.path.exists(p): continue
    try:
        a = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
    except Exception: continue
    if a.shape[0] > 512: continue
    m = ((a[..., 3] > 100) & (a[..., :3].min(axis=2) > 185)).astype(np.float32)
    if m.sum() < 30: continue
    for s, t in tmpls.items():
        th, tw = t.shape
        if th > m.shape[0] or tw > m.shape[1]: continue
        H = m.shape[0] + th; W = m.shape[1] + tw
        F = np.fft.rfft2(m, (H, W)); G = np.fft.rfft2(t[::-1, ::-1], (H, W))
        c = np.fft.irfft2(F * G, (H, W))
        # window sums
        ii = np.pad(m, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        ws = ii[th:, tw:] - ii[:-th, tw:] - ii[th:, :-tw] + ii[:-th, :-tw]
        cc = c[th-1:m.shape[0], tw-1:m.shape[1]]
        score = cc / np.sqrt(np.maximum(ws, 1) * t.sum())
        j = np.unravel_index(np.argmax(score), score.shape)
        res.append((float(score[j]), r[0], r[1], s, j))
res.sort(reverse=True)
for x in res[:25]: print(x)
