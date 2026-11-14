"""ar6_find: find a Japanese word baked into textures by template matching.
ar6_find.py TEXT [--sources A,B] [--heights 14,18,24,32,40] [--mode bright|dark|alpha] [--top 30] [--font BIZUDGothic-Bold.ttf]
Renders TEXT with a gothic font at several heights, binarises each decoded PNG under build/tex (ink = bright pixels, or dark,
or opaque alpha), and ranks by normalised correlation.  Output: score, id, x, y, height."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IDX = os.path.join(ROOT, 'build', 'tex', 'index.tsv')


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def tmpl(text, h, fontfile):
    f = ImageFont.truetype(os.path.join('C:/Windows/Fonts', fontfile), h)
    im = Image.new('L', (h * len(text) + 8, h + 8), 0)
    ImageDraw.Draw(im).text((2, 0), text, font=f, fill=255)
    a = np.asarray(im) > 128
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)


def ncc(img, t):
    H, W = img.shape
    th, tw = t.shape
    if th > H or tw > W:
        return 0, 0, 0
    sh = (H + th, W + tw)
    F = np.fft.rfft2
    I = F(img, sh)
    T = F(t[::-1, ::-1], sh)
    cor = np.fft.irfft2(I * T, sh)[th - 1:H, tw - 1:W]
    ones = np.ones_like(t)
    S2 = np.fft.irfft2(F(img, sh) * F(ones[::-1, ::-1], sh), sh)[th - 1:H, tw - 1:W]
    n = t.sum()
    cov = cor / n
    dens = S2 / t.size
    sc = cov - 0.8 * np.clip(dens - t.mean(), 0, None)
    k = np.unravel_index(np.argmax(sc), sc.shape)
    return sc[k], k[1], k[0]


def main():
    a = sys.argv[1:]
    text = a[0]
    srcs = arg(a, '--sources')
    srcs = srcs.split(',') if srcs else None
    hs = [int(x) for x in arg(a, '--heights', '14,18,24,32,40').split(',')]
    mode = arg(a, '--mode', 'bright')
    top = int(arg(a, '--top', 30))
    ff = arg(a, '--font', 'BIZUDGothic-Bold.ttf')
    ts = {h: tmpl(text, h, ff) for h in hs}
    res = []
    with open(IDX, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for l in f:
            d = dict(zip(hdr, l.rstrip('\n').split('\t')))
            if d['dup_of']:
                continue
            if srcs and not any(d['source'].startswith(s) for s in srcs):
                continue
            if int(d['width']) < 16 or int(d['height']) < 12:
                continue
            p = os.path.join(ROOT, 'build', 'tex', d['source'].replace('/', '__'), d['id'] + '.png')
            if not os.path.exists(p):
                continue
            im = np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)
            L = im[..., :3] @ np.array([.299, .587, .114], np.float32)
            if mode == 'bright':
                ink = ((L > 200) & (im[..., 3] > 100)).astype(np.float32)
            elif mode == 'dark':
                ink = ((L < 60) & (im[..., 3] > 100)).astype(np.float32)
            else:
                ink = (im[..., 3] > 128).astype(np.float32)
            if ink.sum() < 20:
                continue
            best = (0, 0, 0, 0)
            for h, t in ts.items():
                s, x, y = ncc(ink, t)
                if s > best[0]:
                    best = (s, x, y, h)
            res.append((best[0], d['id'], best[1], best[2], best[3], d['source']))
    res.sort(reverse=True)
    for r in res[:top]:
        print('%.3f %s x=%d y=%d h=%d %s' % r)


main()
