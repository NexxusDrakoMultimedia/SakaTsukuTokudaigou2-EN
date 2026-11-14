"""pol: for each ja of the 107 flagged town shorts: which record kinds carry it in HOMETOWN.BIN (tbl / recarr / orphan) and with which en.
Also lists ja groups of the whole file that already have more than one en.  python -I -X utf8 tools/re/pol_kinds.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pol_apply as A
from collections import Counter, defaultdict
rows = [json.loads(l) for l in open(A.PATH, encoding='utf-8') if l.strip()]
by = defaultdict(list)
for r in rows: by[r['ja']].append(r)
def kind(r):
    c = r.get('ctx') or ''
    return 'tbl' if c.startswith('tbl@43858') else 'recarr' if r.get('fmt') == 'recarr' else 'orphan' if r.get('orphan') else 'other'
jas = [v[0] for v in A.NEW.values()]
cnt = Counter()
for ja in jas:
    ks = tuple(sorted(Counter(kind(r) for r in by[ja]).items()))
    cnt[ks] += 1
print(cnt)
for ja in jas[:6]:
    print(ja, [(kind(r), r['en']) for r in by[ja]])
div = [ja for ja, rs in by.items() if len({r['en'] for r in rs}) > 1 and ja not in jas]
print('pre-existing multi-en groups (outside the flagged set):', len(div), div[:10])
print('flagged groups with several en before edit:', sum(1 for ja in jas if len({r['en'] for r in by[ja]}) > 1))
