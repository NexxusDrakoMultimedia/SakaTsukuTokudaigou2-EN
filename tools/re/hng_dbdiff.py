"""hng: diff the English of two snapshots of the translation DB (directories of *.jsonl): which sources / records changed, and a sample.
usage: hng_dbdiff.py OLD_DIR NEW_DIR [SOURCE-substring] [--show N]"""
import glob, json, os, sys
from collections import Counter
old, new = sys.argv[1], sys.argv[2]
src = ''
show = 0
a = sys.argv[3:]
if '--show' in a:
    i = a.index('--show'); show = int(a[i + 1]); del a[i:i + 2]
if a:
    src = a[0]
def load(p):
    d = {}
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln); d[r['id']] = (r.get('en') or '', r.get('skip'))
    return d
tot = Counter(); files = []
for p in sorted(glob.glob(os.path.join(new, '*.jsonl'))):
    fn = os.path.basename(p)
    if src not in fn:
        continue
    q = os.path.join(old, fn)
    if not os.path.isfile(q):
        files.append((fn, 'NEW FILE')); continue
    a_, b_ = load(q), load(p)
    ch = [k for k in b_ if k in a_ and a_[k] != b_[k]]
    add = [k for k in b_ if k not in a_]; rem = [k for k in a_ if k not in b_]
    if ch or add or rem:
        files.append((fn, len(ch), len(add), len(rem)))
        tot['changed'] += len(ch)
        if show:
            for k in ch[:show]:
                print(fn, k, repr(a_[k][0])[:70], '->', repr(b_[k][0])[:70])
for f in files:
    print(f)
print(dict(tot), len(files), 'files differ')
