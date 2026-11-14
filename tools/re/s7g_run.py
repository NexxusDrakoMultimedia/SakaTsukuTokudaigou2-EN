"""s7g_run - repaint the in-match tag textures + FACEMDUL tiles.

    python -I -X utf8 tools/re/s7g_run.py NAME [NAME...] [--scale 3] [--write] [-v]
Jobs live in tools/re/s7g_specs.py.  Writes build/s7g/new/NAME.{before,after,sheet,enc}.png and .pvr;
with --write also translation/textures/<iso path>/<id>.pvr for the texture and every identical copy (each copy its own file).
"""
import os, sys, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import pvr, arttext, texinject
import s7g_specs
OUT = os.path.join(ROOT, 'build', 's7g', 'new')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
INDEX = os.path.join(ROOT, 'build', 'texindex.tsv')


def run(name, scale, write, verbose):
    job = s7g_specs.JOBS[name]
    os.makedirs(OUT, exist_ok=True)
    data = texinject.extract_pvr(job['file'], job['tid'])
    before = Image.fromarray(np.asarray(pvr.decode(data), np.uint8), 'RGBA')
    gl = arttext.load_glossary(os.path.join(ROOT, 'translation', 'glossary.tsv'))
    after, rep = arttext.render_spec(job['spec'], before, HERE, gl, None)
    for w in rep['warnings']:
        print('  WARNING %s: %s' % (name, w))
    if verbose:
        for r in rep['regions']:
            if r.get('font'):
                print('  %-10s %-18r size=%s squash=%s block=%s' % (r['id'], r['text'], r['size'], r['squash'], r['block']))
    before.save(os.path.join(OUT, name + '.before.png'))
    after.save(os.path.join(OUT, name + '.after.png'))
    arttext.before_after(before, after, os.path.join(OUT, name + '.sheet.png'), scale)
    arr = np.asarray(after, np.uint8)
    enc = pvr.encode_ex(arr, original=data)
    chk = pvr.decode(enc.data)
    Image.fromarray(np.asarray(chk, np.uint8), 'RGBA').save(os.path.join(OUT, name + '.enc.png'))
    with open(os.path.join(OUT, name + '.pvr'), 'wb') as f:
        f.write(enc.data)
    diff = int((np.abs(chk.astype(int) - arr.astype(int)).max(axis=2) > 17).sum())
    print('%s: encoded %d bytes, pixels differing >17 after re-encode: %d' % (name, len(enc.data), diff))
    copies = texinject.find_copies(INDEX, job['file'], job['tid'])
    targets = [(c[0], c[1]) for c in copies]
    for f, t in targets:
        orig = texinject.extract_pvr(f, t)
        best = None
        if hasattr(run, 'last'):
            del run.last
        for reserve in (0.25, 0.1, 0.05, 0.4, 0.02, 0.6):
            for seed in (0, 1, 2, 3):
                e = pvr.encode_ex(arr, original=orig, reserve=reserve, seed=seed)
                fc = texinject.fit_check(f, t, e.data)
                if fc['fits']:
                    err = float(np.abs(np.asarray(pvr.decode(e.data), int) - arr.astype(int)).sum())
                    if best is None or err < best[0]:
                        best = (err, e, fc, reserve, seed)
                elif best is None and (not hasattr(run, 'last') or fc['over'] < run.last[0]):
                    run.last = (fc['over'], e, fc)
            if best is not None:
                break
        if best is not None:
            _, e, fc, reserve, seed = best
            print('   encoder reserve=%s seed=%s' % (reserve, seed))
        else:
            e, fc = run.last[1], run.last[2]
        print('  %-22s %-24s fits=%s packed=%s slot=%s' % (f, t, fc['fits'], fc.get('packed'), fc.get('slot')))
        if not fc['fits']:
            print('  DOES NOT FIT by %d' % fc['over']); continue
        if write:
            p = os.path.join(TEXDIR, *f.split('/'), t + '.pvr')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as fh:
                fh.write(e.data)
    if write:
        print('  written %d file(s)' % len(targets))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='+')
    ap.add_argument('--scale', type=int, default=3)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    for n in a.names:
        run(n, a.scale, a.write, a.v)


if __name__ == '__main__':
    main()
