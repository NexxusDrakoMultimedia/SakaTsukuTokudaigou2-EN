"""s8ha: file-level difference of two trial discs (read-only).  usage: s8ha_discdiff.py DIR NAME_A NAME_B"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D   # noqa: E402

A = D.Source(sys.argv[1], sys.argv[2])
B = D.Source(sys.argv[1], sys.argv[3])
fa = {r.path.upper(): r for r in D.read_filesystem(A)[3] if not r.isdir}
fb = {r.path.upper(): r for r in D.read_filesystem(B)[3] if not r.isdir}
print(len(fa), len(fb), 'files')
for p in sorted(fa):
    if p not in fb:
        print('only in A', p)
        continue
    x, y = fa[p], fb[p]
    if (x.lba, x.size) != (y.lba, y.size):
        print('layout differs', p, x.lba, y.lba, x.size, y.size)
    if A.read(x.lba, x.size) != B.read(y.lba, y.size):
        print('content differs', p)
