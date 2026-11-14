"""hsd_sk: independent diff.  usage: hsd_sk_diff.py DISCA DISCB   -> every file whose bytes differ between two trial discs
(by path), plus exact differing byte ranges (gap 1) for SCDRF.BIN / SEARCH.BIN.  Read-only."""
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D

def files(disc):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    return src, {r.path.upper(): r for r in recs if not r.isdir}

def rng(a, b):
    out = []
    for j in range(min(len(a), len(b))):
        if a[j] != b[j]:
            if out and j - out[-1][1] <= 0:
                out[-1][1] = j + 1
            else:
                out.append([j, j + 1])
    return out

A, fa = files(sys.argv[1]); B, fb = files(sys.argv[2])
print('files', len(fa), len(fb), 'only in A', sorted(set(fa) - set(fb))[:5], 'only in B', sorted(set(fb) - set(fa))[:5])
nd = 0
for p in sorted(fa):
    if p not in fb:
        continue
    ra, rb = fa[p], fb[p]
    if ra.size != rb.size:
        print('SIZE', p, ra.size, rb.size); nd += 1; continue
    da = A.read(ra.lba, ra.size); db = B.read(rb.lba, rb.size)
    if da != db:
        nd += 1
        r = rng(da, db)
        print('DIFF', p, 'size', ra.size, 'nranges', len(r), 'bytes', sum(h - l for l, h in r), 'lba', ra.lba, rb.lba)
        if len(sys.argv) > 3 and p.endswith(sys.argv[3].upper()):
            for l, h in r[:40]:
                print('    %x..%x (%d)' % (l, h, h - l))
print('files differing:', nd)
