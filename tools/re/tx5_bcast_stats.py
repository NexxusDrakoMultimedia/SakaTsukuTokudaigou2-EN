"""tx5: statistics of build/tx5/bcast_headers.tsv (made by tx5_bcast_scan.py).  python -I -X utf8 tools/re/tx5_bcast_stats.py"""
import os, sys, collections, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tx5', 'bcast_headers.tsv'), encoding='utf8')][1:]
pre = collections.Counter()
dist = collections.defaultdict(set)
for r in rows:
    nm = r[2]
    folder = nm.split('\\')[0]
    pre[folder] += 1
    dist[folder].add(r[5])
print('folders', len(pre))
for k, v in sorted(pre.items()):
    print(k, v, 'distinct', len(dist[k]))
alltext = collections.Counter(r[5] for r in rows)
print('distinct total', len(alltext))
print('extra nonzero rows', sum(1 for r in rows if len(r) > 6 and r[6]))
tot = sum(len(t.encode('cp932', 'replace')) for t in alltext)
print('distinct bytes', tot)
# any markup chars
mk = collections.Counter()
for t in alltext:
    for m in re.findall(r'[%#@$<>\[\]{}]\w*', t):
        mk[m] += 1
print('markup', mk.most_common(20))
for k in ('放送席', '解説は', '水沼', '八塚'):
    print(k, [r[2] + ' ' + r[5] for r in rows if k in r[5]][:5])
