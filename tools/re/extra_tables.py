"""extra_tables.py [TDB] : one line per table kind (fmt, stride, width): records, overlays carrying it, distinct ja, slot bytes,
example source#offset and texts.  Input of the table in docs/uncovered-text.md."""
import collections
import glob
import json
import os
import re
import sys

tdb = sys.argv[1] if len(sys.argv) > 1 else 'translation'
T = collections.OrderedDict()
for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if '"fmt"' not in line:
            continue
        r = json.loads(line)
        f = r.get('fmt')
        if f not in ('hwptr', 'recarr'):
            continue
        if f == 'recarr':
            m = re.match(r'recarray S=(\d+) n=(\d+) W=(\d+)', r['ctx'])
            key = ('recarr', int(m.group(1)), int(m.group(3)))
        else:
            kind = 'pool' if r['refs'] == 0 else 'ptr'
            key = ('hw' + kind, 0, 4 * ((r['max_bytes'] + 3) // 4))
        t = T.setdefault(key, dict(n=0, src=set(), ja=set(), b=0, ex=[], first=r['id']))
        t['n'] += 1
        t['src'].add(r['id'].rsplit('#', 1)[0])
        t['ja'].add(r['ja'])
        t['b'] += r['max_bytes']
        if len(t['ex']) < 3 and r['ja'] not in t['ex']:
            t['ex'].append(r['ja'])
for k, t in sorted(T.items(), key=lambda kv: -kv[1]['n']):
    print('%-7s S=%-4d W=%-3d records %6d overlays %3d distinct %5d slot-bytes %7d  first %s  %s' % (
        k[0], k[1], k[2], t['n'], len(t['src']), len(t['ja']), t['b'], t['first'], ' | '.join(t['ex'])))
