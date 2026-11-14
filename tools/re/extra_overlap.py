"""extra_overlap.py [TDB] : how many distinct ja of the fmt=hwptr/recarr records already exist as translated text elsewhere."""
import collections
import glob
import json
import os
import sys

tdb = sys.argv[1] if len(sys.argv) > 1 else 'translation'
core_en = {}
core_any = set()
extra = collections.defaultdict(set)
cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(tdb, '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        f = r.get('fmt')
        if f in ('hwptr', 'recarr'):
            extra[f].add(r['ja'])
            cnt[f] += 1
        else:
            core_any.add(r['ja'])
            if r.get('en'):
                core_en[r['ja']] = r['en']
for f, s in extra.items():
    both = sum(1 for j in s if j in core_any)
    done = sum(1 for j in s if j in core_en)
    print('%s: %d records, %d distinct ja; %d of them also occur in older records, %d of those with English already' % (
        f, cnt[f], len(s), both, done))
allx = extra['hwptr'] | extra['recarr']
print('both formats: %d distinct ja, %d already in core records, %d with English' % (
    len(allx), sum(1 for j in allx if j in core_any), sum(1 for j in allx if j in core_en)))
