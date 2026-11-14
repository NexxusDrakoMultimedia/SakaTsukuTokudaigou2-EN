"""hng: compare two build logs (kind, file) rows and notes: which patch classes differ.  usage: hng_logdiff.py OLD.log NEW.log"""
import re
import sys
from collections import OrderedDict


def rows(p):
    d = OrderedDict()
    cur = None
    for ln in open(p, encoding='utf-8', errors='replace'):
        m = re.match(r'^  (\w+)\s+(/\S+)\s+CHANGED (\d+) -> (\d+)', ln)
        if m:
            cur = (m.group(1), m.group(2))
            d[cur] = dict(size=(m.group(3), m.group(4)), line=ln.strip(), notes=[])
        elif ln.startswith('      note:') and cur:
            d[cur]['notes'].append(ln.strip()[6:])
    return d


a, b = rows(sys.argv[1]), rows(sys.argv[2])
kinds = lambda d: sorted({k[0] for k in d})
print('kinds old', kinds(a), 'new', kinds(b))
for k in kinds(b):
    na = sum(1 for x in a if x[0] == k)
    nb = sum(1 for x in b if x[0] == k)
    print('  %-10s old %4d  new %4d' % (k, na, nb))
print('--- only in new (non text kinds):')
for k in b:
    if k not in a and k[0] not in ('overlay', 'ptrblob'):
        print('  ', k, b[k]['notes'][:1])
print('--- only in old:')
for k in a:
    if k not in b:
        print('  ', k)
print('--- in both, different notes (non repack/textures):')
for k in b:
    if k in a:
        na = [n for n in a[k]['notes'] if not n.startswith('note: repack')]
        nb = [n for n in b[k]['notes'] if not n.startswith('note: repack')]
        if na != nb:
            print('  ', k, '\n      old', na[:2], '\n      new', nb[:2])
