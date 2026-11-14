"""l10 survey 3: non-ASCII in fields other than ja; refit ids vs main DB; en containing Japanese (read-only)."""
import collections
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JP = re.compile('[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef\u3000-\u303f]')
main = {}
na = collections.Counter()
ex = collections.defaultdict(list)
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        main[r['id']] = r
        for k, v in r.items():
            if k == 'ja':
                continue
            if isinstance(v, str) and any(ord(c) > 0x7f for c in v):
                kind = 'jp' if JP.search(v) else 'other'
                na[(k, kind)] += 1
                if len(ex[(k, kind)]) < 4:
                    ex[(k, kind)].append((r['id'], v[:60]))
print('main records', len(main), dict(na))
for k, v in ex.items():
    print(k, v)
# refit
nref = bad = missing = 0
na2 = collections.Counter()
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        nref += 1
        m = main.get(r['id'])
        if m is None:
            missing += 1
        elif m['ja'] != r['ja']:
            bad += 1
        for k, v in r.items():
            if k != 'ja' and isinstance(v, str) and JP.search(v):
                na2[k] += 1
print('refit', nref, 'missing in main', missing, 'ja differs', bad, 'jp in other fields', dict(na2))
# duplicates of id
print('dup ids: none' if len(main) == sum(1 for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')) for _ in open(p, encoding='utf-8')) else 'DUP IDS')
