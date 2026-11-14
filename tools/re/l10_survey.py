"""l10 survey: field sets / fmt counts / en==ja identity per translation/*.jsonl (read-only)."""
import collections
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tot = collections.Counter()
keysets = collections.Counter()
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    n = 0
    fm = collections.Counter()
    ident = empty = skip = 0
    samples = {}
    for line in open(p, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        f = r.get('fmt', '')
        fm[f] += 1
        keysets[tuple(sorted(r))] += 1
        if r.get('en') == '':
            empty += 1
        elif r.get('en') == r.get('ja'):
            ident += 1
        if r.get('skip'):
            skip += 1
        samples.setdefault(f, r)
    tot['n'] += n
    tot['ident'] += ident
    tot['empty'] += empty
    tot['skip'] += skip
    print('%-45s n=%6d empty=%6d ident=%6d skip=%d fmt=%s' % (os.path.basename(p), n, empty, ident, skip, dict(fm)))
    if len(sys.argv) > 1:
        for f, r in samples.items():
            print('   ', json.dumps(r, ensure_ascii=False)[:300])
print(dict(tot))
for k, v in keysets.most_common():
    print(v, k)
