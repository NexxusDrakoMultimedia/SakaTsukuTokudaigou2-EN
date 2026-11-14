"""skp: per-file count of table-short records whose en equals one of the 107 new forms with the matching ja (and old->new vs baseline)
    python -I -X utf8 tools/re/skp_perfile.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
import pol_apply as A
newja = {v[0]: v[1] for v in A.NEW.values()}
tot = 0
for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
    if not fn.endswith('.jsonl'): continue
    n = 0; ids = set()
    for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)
        if 'tbl@' in (r.get('ctx') or '') and newja.get(r['ja']) == r['en']:
            n += 1; ids.add(r['ja'])
    if n: print(fn, n, len(ids)); tot += n
print('total', tot)
