"""s8ft: file-by-file diff of two trial discs (hsk_full1 vs s8e_nofix etc.), one line per changed file, with byte counts.
usage: s8ft_alldiff.py A B [PATTERN]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D  # noqa: E402


def load(name):
    d = os.path.join(ROOT, 'build', 'trial')
    if os.path.isdir(os.path.join(d, name)):
        d = os.path.join(d, name)
    src = D.Source(d, name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    return src, {r.path.upper(): r for r in recs if not r.isdir}


sa, fa = load(sys.argv[1])
sb, fb = load(sys.argv[2])
pat = sys.argv[3].upper() if len(sys.argv) > 3 else None
for p in sorted(set(fa) & set(fb)):
    if pat and pat not in p:
        continue
    ra, rb = fa[p], fb[p]
    da = sa.read(ra.lba, ra.size)
    db = sb.read(rb.lba, rb.size)
    if da == db:
        continue
    n = min(len(da), len(db))
    nd = sum(1 for i in range(n) if da[i] != db[i]) if n < 3000000 else -1
    print('%-34s size %d/%d lba %d/%d diffbytes %d' % (p, ra.size, rb.size, ra.lba, rb.lba, nd))
