"""recarr_survey.py [SOURCE..] : run textfmt_recarray.find_arrays on every overlay; print fixed-slot arrays that have members
no existing record covers."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T
import textfmt_recarray as R
import textfmt_common as C

srcs = sys.argv[1:] or [s for s, _ in T.list_sources()]
tot = 0
for src in srcs:
    t0 = time.time()
    try:
        img = T.load_image(src)
    except ValueError:
        continue
    strs, ptrs, _ = T.extract_image(img)
    ex = [(s.off, s.off + s.max_bytes) for s in strs]
    arrs = R.find_arrays(img.data, img.base)
    recs = R.extract(img.data, src, ex, arrs)
    by = {}
    for r in recs:
        by.setdefault(r['ctx'], []).append(r)
    print('%-26s arrays %3d fixed %3d new records %5d  (%.1fs)' % (src, len(arrs), sum(1 for a in arrs if a.width), len(recs), time.time() - t0))
    for ctx, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print('      %-34s new=%-5d %s' % (ctx, len(rs), ' | '.join(r['ja'] for r in rs[:4])))
    tot += len(recs)
print('TOTAL new records', tot)
