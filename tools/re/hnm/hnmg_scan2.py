import collections, re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import hnmg_scan as S
recs = S.load()
by = collections.defaultdict(collections.Counter)
for f, ln, r in recs:
    by[(r['ja'])][r['en']] += 1
dist = [k for k in by if k.endswith('郡') or k.endswith('群')]
print(len(dist), 'district ja')
g = sum(1 for k in dist if any(e.endswith('-gun') for e in by[k]))
print('with gun en:', g)
for k in dist[:12]:
    print(k, dict(by[k]))
# non-district ending with gun?
print([ (k, dict(v)) for k, v in by.items() if k not in dist and any('gun' in e for e in v)][:10])
# per-file counts for gun-ful
cc = collections.Counter(); ctxs = collections.Counter()
for f, ln, r in recs:
    if r['en'].endswith('-gun'):
        ctxs[re.sub(r'\[.*', '', r['ctx'])] += 1
print(ctxs.most_common(40))
print(collections.Counter(r['ctx'][:0]+str(r['max_bytes']) for f,l,r in recs if r['en'].endswith('-gun')))
