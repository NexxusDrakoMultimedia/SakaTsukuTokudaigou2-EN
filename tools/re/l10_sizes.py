"""l10 sizes: which fields make the l10n files big (read-only). usage: l10_sizes.py DIR"""
import collections
import glob
import json
import os
import sys

d = sys.argv[1]
sz = collections.Counter()
n = 0
ctxs = collections.Counter()
for p in glob.glob(os.path.join(d, '*.jsonl')):
    for line in open(p, encoding='utf-8').read().split('\n')[1:]:
        if not line:
            continue
        r = json.loads(line)
        n += 1
        for k, v in r.items():
            sz[k] += len(json.dumps(v, ensure_ascii=False)) + len(k) + 4
        c = r.get('ctx')
        if c is not None:
            ctxs[c] += 1
print('records', n, 'total', sum(sz.values()))
for k, v in sz.most_common():
    print('%-10s %12d' % (k, v))
print('distinct ctx', len(ctxs), 'top:')
tot = sum(len(c) * v for c, v in ctxs.items())
print('ctx bytes', tot)
for c, v in ctxs.most_common(8):
    print(v, c)
