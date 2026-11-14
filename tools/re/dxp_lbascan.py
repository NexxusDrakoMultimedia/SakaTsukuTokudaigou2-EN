"""Read-only: does ANY file on the disc contain a 4-aligned u32 equal to the start LBA (or FAD = LBA+150),
the size in bytes, or the sector count of any other file / the disc end?  numpy.  usage: dxp_lbascan.py"""
import os, sys, collections
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
files = [r for r in recs if not r.isdir]
lba = {r.lba: r.path for r in files if r.size}
fad = {r.lba + 150: r.path for r in files if r.size}
size = collections.defaultdict(list)
for r in files:
    if r.size >= 4096:
        size[r.size].append(r.path)
nsec = collections.defaultdict(list)
for r in files:
    if D._nsec(r.size) >= 64:
        nsec[D._nsec(r.size)].append(r.path)
specials = {549150: 'disc end', 549300: 'end FAD', 504150: 'vol size', 45000: 'HD base', 45150: 'HD base FAD', 56665: 'T5 start', 56890: 'data start'}
keys = {}
for k, v in lba.items(): keys[('lba', k)] = v
tot = collections.Counter()
rows = []
lba_arr = np.array(sorted(lba), dtype=np.uint32)
fad_arr = np.array(sorted(fad), dtype=np.uint32)
size_arr = np.array(sorted(size), dtype=np.uint32)
nsec_arr = np.array(sorted(nsec), dtype=np.uint32)
spec_arr = np.array(sorted(specials), dtype=np.uint32)
for r in sorted(files, key=lambda r: r.lba):
    d = src.read(r.lba, r.size)
    n = len(d) // 4
    w = np.frombuffer(d[:n * 4], dtype='<u4')
    for name, arr, tbl in (('lba', lba_arr, lba), ('fad', fad_arr, fad), ('size', size_arr, size), ('nsec', nsec_arr, nsec), ('special', spec_arr, specials)):
        m = np.isin(w, arr)
        c = int(m.sum())
        if c:
            idx = np.nonzero(m)[0]
            vals = sorted(set(int(w[i]) for i in idx))
            rows.append((r.path, name, c, vals[:6], [hex(int(i) * 4) for i in idx[:4]]))
            tot[name] += c
for row in rows:
    print(*row)
print('totals', dict(tot), 'files scanned', len(files))
