"""ar6_scan: automatic pre-filter for textures that carry text-like ink.
Usage: ar6_scan.py [--only SUBSTR]   (writes build/ar6/scan.tsv)
For every distinct (dup_of empty) record of build/tex/index.tsv, score the decoded PNG for dense small high-contrast
strokes arranged in horizontal bands (words).  Sorted by number of word-runs.  'installed' = a repainted texture exists."""
import os, sys
import numpy as np
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IDX = os.path.join(ROOT, 'build', 'tex', 'index.tsv')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
BS = chr(92)


def installed():
    s = set()
    for dp, dn, fn in os.walk(TEXDIR):
        for f in fn:
            if f.endswith('.pvr'):
                s.add(os.path.relpath(os.path.join(dp, f), TEXDIR).replace(BS, '/')[:-4])
    return s


def score(path):
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    if W < 24 or H < 12:
        return 0, 0, 0
    al = a[..., 3] / 255.0
    L = (a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114) * al + 128 * (1 - al)
    gx = np.abs(np.diff(L, axis=1))[:-1, :]
    gy = np.abs(np.diff(L, axis=0))[:, :-1]
    e = ((gx > 70) | (gy > 70))
    h2, w2 = e.shape
    bs = 8
    hh, ww = h2 // bs, w2 // bs
    if hh < 1 or ww < 2:
        return 0, 0, 0
    blk = e[:hh * bs, :ww * bs].reshape(hh, bs, ww, bs).mean((1, 3))
    texty = (blk > 0.18) & (blk < 0.65)
    vx = (gx[:hh * bs, :ww * bs] > 70).reshape(hh, bs, ww, bs).mean((1, 3))
    vy = (gy[:hh * bs, :ww * bs] > 70).reshape(hh, bs, ww, bs).mean((1, 3))
    texty &= (vx > 0.06) & (vy > 0.06)
    frac = texty.mean()
    runs = 0
    for r in range(hh):
        c = 0
        for v in texty[r]:
            if v:
                c += 1
            else:
                if c >= 4:
                    runs += 1
                c = 0
        if c >= 4:
            runs += 1
    return frac, runs, int(texty.sum())


def main():
    a = sys.argv[1:]
    only = a[a.index('--only') + 1] if '--only' in a else None
    outp = os.path.join(ROOT, 'build', 'ar6', 'scan%s.tsv' % ('_' + only.strip('/').replace('/', '_') if only else ''))
    inst = installed()
    rows = []
    with open(IDX, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for l in f:
            d = dict(zip(hdr, l.rstrip('\n').split('\t')))
            if d['dup_of']:
                continue
            if only and only not in d['source']:
                continue
            rows.append(d)
    res = []
    for d in rows:
        cont = d['source'].replace('/', '__')
        p = os.path.join(ROOT, 'build', 'tex', cont, d['id'] + '.png')
        if not os.path.exists(p):
            continue
        key = (d['source'] + '/' + d['member'] + '#' + d['rec']) if d['member'] else (d['source'] + '/#' + d['rec'])
        try:
            fr, runs, n = score(p)
        except Exception:
            continue
        res.append((fr, runs, n, d['id'], d['source'], d['member'], d['width'], d['height'], d['format'], int(key in inst)))
    res.sort(key=lambda r: -r[1])
    with open(outp, 'w', encoding='utf8') as f:
        f.write('frac\truns\tn\tid\tsource\tmember\tw\th\tformat\tinstalled\n')
        for r in res:
            f.write('\t'.join(('%.3f' % x) if isinstance(x, float) else str(x) for x in r) + '\n')
    print(len(res), 'scored ->', outp)


main()
