"""fw_census.py SOURCE : read-only census of the translation records of one source by (fmt, ctx class, max_bytes).
Field-width feasibility study (docs/expansion/field-widths.md)."""
import json, sys, re, collections
src = sys.argv[1]
p = 'translation/%s.jsonl' % src.replace('/', '__')
C = collections.Counter()
ex = {}
for ln in open(p, encoding='utf8'):
    r = json.loads(ln)
    ctx = re.sub(r'[0-9a-f]{3,}|\d+', 'N', r.get('ctx') or '')
    k = (r.get('fmt'), ctx[:60], r['max_bytes'])
    C[k] += 1
    ex.setdefault(k, (r['id'], r['ja'], r['en']))
for k, n in sorted(C.items(), key=lambda x: -x[1])[:int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
    print(n, k, ex[k])
