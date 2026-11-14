"""s7n: full diff of two overlay dirs by id (not only my ja).  usage: s7n_ovdiff.py DIR_A DIR_B   -> counts + the first lines of each kind"""
import glob
import json
import os
import sys
import collections

def load(d):
    out = {}
    for p in glob.glob(os.path.join(d, '*.jsonl')):
        for ln in open(p, encoding='utf8'):
            if ln.strip():
                r = json.loads(ln)
                out[r['id']] = r
    return out

a, b = load(sys.argv[1]), load(sys.argv[2])
only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
chg = sorted(i for i in set(a) & set(b) if a[i]['en'] != b[i]['en'])
print('only in A: %d, only in B: %d, changed: %d' % (len(only_a), len(only_b), len(chg)))
ca = collections.Counter((a[i]['ja'], a[i]['en']) for i in only_a)
cb = collections.Counter((b[i]['ja'], b[i]['en']) for i in only_b)
cc = collections.Counter((a[i]['ja'], a[i]['en'], b[i]['en']) for i in chg)
print('ONLY A (dropped in B):')
for k, v in ca.most_common(40):
    print('  ', v, k)
print('ONLY B (new in B):')
for k, v in cb.most_common(40):
    print('  ', v, k)
print('CHANGED:')
for k, v in cc.most_common(20):
    print('  ', v, k)
