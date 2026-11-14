"""ar5_find: find a sprite (alpha mask of a rect of one decoded texture) in every other texture of the disc.

    python -I -X utf8 tools/re/ar5_find.py SRC TID X Y W H [--thr 0.9] [--dirs ETC_DATA,FLOW_PRG] [--minw N]

Lists (file, id, x, y, iou) for every texture whose alpha mask contains the sprite, NOT only identical payloads."""
import os, sys, argparse
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr, texinject, art7_match  # noqa

TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('tid')
    ap.add_argument('x', type=int); ap.add_argument('y', type=int); ap.add_argument('w', type=int); ap.add_argument('h', type=int)
    ap.add_argument('--thr', type=float, default=0.9)
    ap.add_argument('--dirs', default='')
    ap.add_argument('--alpha', type=int, default=128)
    ap.add_argument('--luma', type=int, default=-1, help='use luma > N as the mask instead of alpha')
    a = ap.parse_args()
    cache = {}

    def blob(rel):
        if rel not in cache:
            with open(os.path.join(ROOT, 'extracted', *rel.split('/')), 'rb') as f:
                cache.clear()
                cache[rel] = f.read()
        return cache[rel]

    def mask(arr):
        if a.luma >= 0:
            return (arr[..., :3].astype(float) @ np.array([.299, .587, .114]) > a.luma) & (arr[..., 3] >= 64)
        return arr[..., 3] >= a.alpha
    ref_arr = np.asarray(pvr.decode(texinject.extract_pvr(blob(a.src), a.tid))).copy()
    ref = mask(ref_arr)[a.y:a.y + a.h, a.x:a.x + a.w]
    print('ref ink px', int(ref.sum()), 'of', ref.size)
    dirs = [d for d in a.dirs.split(',') if d]
    seen = set()
    rows = []
    with open(TEXIDX, encoding='utf8') as f:
        f.readline()
        for l in f:
            p = l.rstrip('\n').split('\t')
            if len(p) < 13 or p[1] == '!':
                continue
            if dirs and p[0].split('/')[0] not in dirs:
                continue
            if int(p[5]) < a.w or int(p[6]) < a.h:
                continue
            rows.append(p)
    rows.sort(key=lambda p: p[0])
    for p in rows:
        k = (p[12], p[3], p[5], p[6])
        if k in seen:
            continue
        seen.add(k)
        try:
            arr = np.asarray(pvr.decode(texinject.extract_pvr(blob(p[0]), p[1]))).copy()
        except Exception as e:  # noqa
            continue
        m = mask(arr)
        # reuse art7_match on a fake RGBA with alpha = mask
        fake = np.zeros(arr.shape[:2] + (4,), np.uint8)
        fake[..., 3] = m * 255
        for (x, y, v) in art7_match.find(fake, ref, a.thr, 4):
            print('%-30s %-16s x=%d y=%d iou=%.3f  (%s %sx%s)' % (p[0], p[1], x, y, v, p[3], p[5], p[6]))
            sys.stdout.flush()


if __name__ == '__main__':
    main()
