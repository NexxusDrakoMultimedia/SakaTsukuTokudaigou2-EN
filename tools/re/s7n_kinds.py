"""s7n: for the exact-name hits (ja equals an entry) tabulate (key, kind, table size n) counts.  usage: s7n_kinds.py scan.tsv"""
import sys, re, collections
c = collections.Counter()
ex = {}
for l in open(sys.argv[1], encoding='utf8'):
    p = l.rstrip('\n').split('\t')
    if len(p) < 6 or not p[0].startswith('F'):
        continue
    ctx = p[5]
    m = re.search(r'tbl@[0-9a-f]+\[\d+/(\d+)\]', ctx)
    n = m.group(1) if m else '-'
    kind = 'hwpool' if 'hwpool' in ctx else ('hwptr' if 'hwptr' in ctx else ('ptr' if 'ptr@' in ctx else ('orphan' if 'orphan' in ctx else ('bcast' if p[1].startswith('BCAST') else 'other'))))
    if len(p[2]) > 14:
        kind += '+long'
    c[(kind, n)] += 1
    ex.setdefault((kind, n), p[1] + ' ' + p[2][:20])
for k, v in sorted(c.items()):
    print(k, v, ex[k])
