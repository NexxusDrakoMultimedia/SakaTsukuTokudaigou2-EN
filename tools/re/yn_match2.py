import csv, os
import numpy as np
from PIL import Image
S = os.environ.get('SAKATSUKU_SCRATCH', os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')), 'build', 'scratch')) + '/'
im = Image.open(S + 'images/51.webp').convert('RGB')
k = 640 / 984
crop = im.crop((75, 378, 196, 421))
w, h = crop.size
def tm(scale):
    c = crop.resize((int(w * k * scale), int(h * k * scale)), Image.LANCZOS)
    a = np.asarray(c).astype(np.float32)
    g = a.min(axis=2)
    g = np.clip((g - 120) / 100.0, 0, 1)   # whiteness
    return g
tm_all = {s: tm(s) for s in (1.0, 0.75, 1.5)}
rows = list(csv.reader(open('build/tex/index.tsv', encoding='utf-8'), delimiter='\t'))
res = []
def box_sum(a, th, tw):
    ii = np.pad(a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    return ii[th:, tw:] - ii[:-th, tw:] - ii[th:, :-tw] + ii[:-th, :-tw]
for r in rows[1:]:
    if not r[12]: continue
    if int(r[4]) > 256 or int(r[5]) > 256: continue
    p = os.path.join('build/tex', r[1].replace('/', '__'), r[0] + '.png')
    if not os.path.exists(p): continue
    try: a = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
    except Exception: continue
    g = np.clip((a[..., :3].min(axis=2) - 150) / 80.0, 0, 1) * (a[..., 3] > 100)
    if g.sum() < 40: continue
    for s, t in tm_all.items():
        th, tw = t.shape
        if th > g.shape[0] or tw > g.shape[1]: continue
        t0 = t - t.mean()
        H = g.shape[0] + th; W = g.shape[1] + tw
        c = np.fft.irfft2(np.fft.rfft2(g, (H, W)) * np.fft.rfft2(t0[::-1, ::-1], (H, W)), (H, W))
        cc = c[th-1:g.shape[0], tw-1:g.shape[1]]
        n = th * tw
        s1 = box_sum(g, th, tw); s2 = box_sum(g * g, th, tw)
        var = np.maximum(s2 - s1 * s1 / n, 1e-3)
        score = cc / np.sqrt(var * (t0 ** 2).sum())
        j = np.unravel_index(np.argmax(score), score.shape)
        res.append((float(score[j]), r[0], r[1], s, (int(j[0]), int(j[1]))))
res.sort(reverse=True)
for x in res[:30]: print(x, flush=True)
