"""Statistics of the translation DB: distinct Japanese texts per source and overall, bytes, empty-en counts."""
import json, glob, os, collections
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
tot = 0
distinct = {}
per = collections.Counter()
perd = collections.defaultdict(set)
have = 0
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    name = os.path.basename(f)
    for line in open(f, encoding='utf8'):
        if not line.strip():
            continue
        r = json.loads(line)
        tot += 1
        per[name] += 1
        perd[name].add(r['ja'])
        distinct.setdefault(r['ja'], 0)
        distinct[r['ja']] += 1
        if r.get('en'):
            have += 1
print('records', tot, 'with en', have, 'distinct ja', len(distinct))
print('distinct ja bytes (utf8 chars):', sum(len(k) for k in distinct))
single = sum(1 for k, v in distinct.items() if v == 1)
print('distinct appearing once', single)
rows = sorted(per.items(), key=lambda x: -x[1])
for n, c in rows[:25]:
    print('%-40s records %6d distinct %6d' % (n, c, len(perd[n])))
print('files', len(per))
