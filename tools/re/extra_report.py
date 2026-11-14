"""extra_report.py [TDB_DIR] : counts / byte budgets of the fmt=hwptr / fmt=recarr records per source and per table kind."""
import collections
import glob
import json
import os
import re
import sys

tdb = sys.argv[1] if len(sys.argv) > 1 else 'translation'
per_src = collections.defaultdict(lambda: collections.Counter())
tables = collections.defaultdict(lambda: [0, 0, set(), []])      # key -> [records, slot bytes, distinct ja, examples]
for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if '"fmt"' not in line:
            continue
        r = json.loads(line)
        f = r.get('fmt')
        if f not in ('hwptr', 'recarr'):
            continue
        src = r['id'].rsplit('#', 1)[0]
        per_src[src][f] += 1
        ctx = r['ctx']
        if f == 'recarr':
            m = re.match(r'recarray S=(\d+) n=(\d+) W=(\d+)', ctx)
            key = 'recarr S=%s W=%s' % (m.group(1), m.group(3))
        else:
            key = 'hwptr slot<=%d' % (4 * ((r['max_bytes'] + 3) // 4))
        t = tables[key]
        t[0] += 1
        t[1] += r['max_bytes']
        t[2].add(r['ja'])
        if len(t[3]) < 4:
            t[3].append(r['ja'])
print('sources with extra records:', len(per_src))
tot = collections.Counter()
for s, c in sorted(per_src.items()):
    tot.update(c)
print('TOTAL', dict(tot))
for k, (n, b, d, ex) in sorted(tables.items(), key=lambda kv: -kv[1][0])[:40]:
    print('%-24s records %6d  distinct ja %5d  slot bytes %7d  %s' % (k, n, len(d), b, ' | '.join(ex)))
