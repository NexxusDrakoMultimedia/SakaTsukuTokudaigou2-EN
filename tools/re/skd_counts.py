"""skd_counts: recount table records (fmt recarr / hwptr) and totals from translation/*.jsonl.  Read-only."""
import collections, glob, json, os
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
c = collections.Counter(); en = collections.Counter(); skip = collections.Counter()
for f in glob.glob(os.path.join(R, 'translation', '*.jsonl')):
    for line in open(f, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        k = r.get('fmt', '?')
        c[k] += 1
        if r.get('en'):
            en[k] += 1
        if r.get('skip') or r.get('hint') == 'skip':
            skip[k] += 1
print('total', sum(c.values()), 'with en', sum(en.values()))
for k in c:
    print(k, c[k], en[k], skip[k])
