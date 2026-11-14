"""art4_run - repaint the group-4 textures (secretary, staff and recruiting menus).

    python -I -X utf8 tools/re/art4_run.py NAME [NAME...] [--scale 3] [--write]
Jobs live in tools/re/art4_specs.py (JOBS: name -> dict(file, tid, dups, spec)).  Writes build/art4/NAME.{before,after,sheet}.png;
with --write also translation/textures/<iso path>/<tid>.pvr for the texture and every dup copy.
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import numpy as np                      # noqa: E402
from PIL import Image                   # noqa: E402
import pvr                              # noqa: E402
import arttext                          # noqa: E402
import texinject                        # noqa: E402
import art4_specs                       # noqa: E402
import art4_specs_b                     # noqa: E402,F401  (adds more jobs to art4_specs.JOBS)

OUT = os.path.join(ROOT, 'build', 'art4')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')


def rowmode(arr, rect, ink, dilate=0, exclude=(), rad=0):
    """Erase the ink inside rect by filling every masked pixel with the most frequent colour of the clean pixels of its
    own row (bars whose profile is constant along x); rows without clean pixels copy the previous filled row."""
    from collections import Counter
    H, W = arr.shape[:2]
    x, y, w, h = rect
    if isinstance(ink, dict):
        ink = [ink]
    m = np.zeros((h, w), bool)
    for c in ink:
        m |= arttext._cond_mask(c, arr, rect, '.', W, H)
    if dilate:
        m = arttext._dilate(m, dilate)
    for rx, ry, rw, rh in exclude:
        x0, y0, x1, y1 = max(rx, x), max(ry, y), min(rx + rw, x + w), min(ry + rh, y + h)
        if x1 > x0 and y1 > y0:
            m[y0 - y:y1 - y, x0 - x:x1 - x] = False
    rad = rad or 0
    prev = None
    for j in range(h):
        row = arr[y + j, x:x + w]
        clean = ~m[j]
        keys = [tuple(v) for v in np.rint(row).astype(int)]
        gval = None
        if clean.sum() >= 4:
            gval = np.array(Counter(k for k, c in zip(keys, clean) if c).most_common(1)[0][0], float)
        elif prev is not None:
            gval = prev
        if gval is None:
            continue
        out = row.copy()
        for i in np.nonzero(m[j])[0]:
            val = gval
            if rad < 0:
                cl = np.nonzero(clean)[0]
                if len(cl):
                    k = cl[np.argmin(np.abs(cl - i))]
                    val = np.array(keys[k], float)
            elif rad:
                lo, hi = max(0, i - rad), min(w, i + rad + 1)
                cnt = Counter(keys[k] for k in range(lo, hi) if clean[k])
                if len(cnt) and sum(cnt.values()) >= 3:
                    val = np.array(cnt.most_common(1)[0][0], float)
            out[i] = val
        row[:] = out
        prev = gval


def run(name, scale, write):
    job = art4_specs.JOBS[name]
    os.makedirs(OUT, exist_ok=True)
    data = texinject.extract_pvr(job['file'], job['tid'])
    before = Image.fromarray(np.asarray(pvr.decode(data), np.uint8), 'RGBA')
    spec = job['spec']
    base = np.asarray(before, np.float64).copy()
    for op in job.get('pre', []):
        rowmode(base, op['rect'], op['ink'], op.get('dilate', 0), op.get('exclude', ()), op.get('rad', 0))
    if job.get('pre'):
        before_clean = Image.fromarray(np.clip(np.rint(base), 0, 255).astype(np.uint8), 'RGBA')
    else:
        before_clean = before
    gl = arttext.load_glossary(os.path.join(ROOT, 'translation', 'glossary.tsv'))
    after, rep = arttext.render_spec(spec, before_clean, HERE, gl, None)
    for w in rep['warnings']:
        print('  WARNING %s: %s' % (name, w))
    for r in rep['regions']:
        if r.get('font') and '-v' in sys.argv:
            print('  %-12s %-22r size=%s squash=%s block=%s' % (r['id'], r['text'], r['size'], r['squash'], r['block']))
    before.save(os.path.join(OUT, name + '.before.png'))
    after.save(os.path.join(OUT, name + '.after.png'))
    arttext.before_after(before, after, os.path.join(OUT, name + '.sheet.png'), scale)
    arr = np.asarray(after, np.uint8)
    res = texinject.encode_via = None
    enc = pvr.encode_ex(arr, original=data)
    chk = pvr.decode(enc.data)
    Image.fromarray(np.asarray(chk, np.uint8), 'RGBA').save(os.path.join(OUT, name + '.enc.png'))
    diff = int((np.abs(chk.astype(int) - arr.astype(int)).max(axis=2) > 17).sum())
    print('%s: encoded %d bytes, pixels differing >17 after re-encode: %d' % (name, len(enc.data), diff))
    # fit check
    targets = [(job['file'], job['tid'])] + list(job.get('dups', []))
    for f, t in targets:
        orig = texinject.extract_pvr(f, t)
        e = pvr.encode_ex(arr, original=orig)
        texinject.replace_texture(f, t, e.data, 'exact')       # raises FitError when too big
        if write:
            p = os.path.join(TEXDIR, *f.split('/'), t + '.pvr')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as fh:
                fh.write(e.data)
    print('  fits in slot: %d target(s)%s' % (len(targets), ', written' if write else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='+')
    ap.add_argument('--scale', type=int, default=3)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    for n in a.names:
        run(n, a.scale, a.write)


if __name__ == '__main__':
    main()
