"""hwpool_survey.py : per overlay, how many hwptr records are pool (unreferenced) strings, and samples."""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T
import textfmt_hwkana as H
tot = collections.Counter()
for src, _ in T.list_sources():
    if src == '1ST_READ.BIN':
        continue
    try:
        img = T.load_image(src)
    except ValueError:
        continue
    strs, ptrs, _ = T.extract_image(img)
    ex = [(s.off, s.off + s.max_bytes) for s in strs]
    recs = H.extract(img.data, img.base, src, ex)
    pool = [r for r in recs if r['refs'] == 0]
    if pool:
        runs = collections.Counter(r['ctx'] for r in pool)
        print('%-26s ptr %5d pool %5d  runs %s  %s' % (src, len(recs) - len(pool), len(pool), sorted({int(c.split('run=')[1].split()[0]) for c in runs}), ' '.join(r['ja'] for r in pool[:6])))
    tot['ptr'] += len(recs) - len(pool)
    tot['pool'] += len(pool)
print(dict(tot))
