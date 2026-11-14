"""s7n: group scan hits by (key, ja, en) with counts and sample ids.  usage: s7n_group.py scan.tsv out.txt"""
import sys, collections
rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1], encoding='utf8') if l.strip()]
g = collections.OrderedDict()
for r in rows:
    k = (r[0], r[2], r[3], r[4])
    g.setdefault(k, []).append(r[1])
out = []
for k, ids in g.items():
    out.append('%s\t%s\t%s\tmax=%s\tn=%d\t%s' % (k[0], k[1], k[2], k[3], len(ids), ' '.join(ids[:2])))
open(sys.argv[2], 'w', encoding='utf8').write('\n'.join(out) + '\n')
print(len(out), 'groups')
