"""s7n: static check results (tools/refit) of one candidate English for every record of a ja, grouped.

usage: s7n_chk.py JA EN CLS      e.g. s7n_chk.py ﾚｯｽﾞ "Red Diamonds" jclub
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import refit as RF  # noqa: E402
import build_patch as BP  # noqa: E402

by_src = BP.load_tdb('translation')
ja, en, cls = sys.argv[1:4]
c = collections.Counter()
for src, recs in by_src.items():
    for r in recs:
        if r['ja'] != ja:
            continue
        bad = RF.check_hard(r, en, True)
        cc = RF.check_class(by_src, r, en, cls)
        msg = ('hard %s' % (bad,)) if bad else ('; '.join('%s %s' % x for x in cc) if cc else 'ok')
        c[(r.get('fmt'), (r.get('ctx') or '')[:30], msg[:130])] += 1
for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:25]:
    print(v, k)
