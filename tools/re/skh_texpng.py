"""skh: write before/after PNGs of textures, original (extracted/) vs a built trial disc.

usage: skh_texpng.py DISC FILE TID OUTDIR   (FILE like ETC_DATA/SHTEX.ZAR, TID like frame.tbd#3; TID may be 'all')
Writes OUTDIR/<file>_<tid>_orig.png and _new.png side by side in one file <..>_cmp.png (orig left, new right, magenta line between).
Read-only on the project.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402
import texinject as T            # noqa: E402
import pvr as P                  # noqa: E402
import numpy as np               # noqa: E402
from PIL import Image            # noqa: E402


def disc_file(name, rel):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    r = files['/' + rel.upper()]
    d = src.read(r.lba, r.size)
    src.close()
    return d


def decode_tid(data, tid):
    pv = T.extract_pvr(data, tid)
    return P.decode(pv)


def main(argv):
    disc, rel, tid, out = argv[1:5]
    os.makedirs(out, exist_ok=True)
    new = disc_file(disc, rel)
    with open(os.path.join(ROOT, 'extracted', rel), 'rb') as f:
        old = f.read()
    tids = [t.tid for t in T.list_textures(old)] if tid == 'all' else [tid]
    for t in tids:
        try:
            a = decode_tid(old, t)
            b = decode_tid(new, t)
        except Exception as e:
            print('skip', t, e)
            continue
        same = (a.shape == b.shape) and bool((a == b).all())
        if tid == 'all' and same:
            continue
        h = max(a.shape[0], b.shape[0])
        canvas = np.zeros((h, a.shape[1] + b.shape[1] + 4, 4), dtype=np.uint8)
        canvas[:, :, 0] = 255
        canvas[:, :, 2] = 255
        canvas[:, :, 3] = 255
        canvas[:a.shape[0], :a.shape[1]] = a
        canvas[:b.shape[0], a.shape[1] + 4:] = b
        fn = os.path.join(out, '%s_%s_cmp.png' % (rel.replace('/', '_'), t.replace('#', '_').replace('@', 'at')))
        Image.fromarray(canvas, 'RGBA').save(fn)
        print('%s %s %s same=%s -> %s' % (rel, t, a.shape, same, fn))


if __name__ == '__main__':
    main(sys.argv)
