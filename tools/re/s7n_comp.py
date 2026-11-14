"""s7n: distinct short competition-name records (key C) from scanC.tsv: ja, en, count, kinds.  usage: s7n_comp.py scanC.tsv out.txt"""
import sys, collections
g = collections.OrderedDict()
for l in open(sys.argv[1], encoding='utf8'):
    p = l.rstrip('\n').split('\t')
    if len(p) < 6 or p[0] != 'C' or len(p[2]) > 26:
        continue
    k = (p[2], p[3])
    g.setdefault(k, []).append((p[1], p[4], p[5][:50]))
with open(sys.argv[2], 'w', encoding='utf8') as fh:
    for (ja, en), v in g.items():
        fh.write('%s\t%s\tn=%d\tmax=%s\t%s\t%s\n' % (ja, en, len(v), v[0][1], v[0][0], v[0][2]))
print(len(g))
