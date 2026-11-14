"""Read-only: disc layout survey (files by dir/size, gaps, duplicates). prefix dxp_"""
import sys, os, hashlib, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
files = [r for r in recs if not r.isdir]
dirs = [r for r in recs if r.isdir]
print('files', len(files), 'dirs', len(dirs), 'end', src.end_lba)
tot = sum(r.size for r in files)
print('total file bytes', tot, 'sectors', sum(D._nsec(r.size) for r in files))
# per top dir
agg = collections.defaultdict(lambda: [0, 0, 0])
for r in files:
    top = r.path.split('/')[1] if r.path.count('/') > 1 else '(root)'
    a = agg[top]; a[0] += 1; a[1] += r.size; a[2] += D._nsec(r.size)
for k, v in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    print('%-12s files=%5d bytes=%12d sectors=%7d' % (k, *v))
print('--- biggest 25')
for r in sorted(files, key=lambda r: -r.size)[:25]:
    print('%10d lba=%7d %s' % (r.size, r.lba, r.path))
print('--- root files')
for r in sorted(files, key=lambda r: r.lba):
    if r.path.count('/') == 1:
        print('%10d lba=%7d %s' % (r.size, r.lba, r.path))
ext = D.used_extents(src, pvd, rl, rs, recs)
gaps = D.free_gaps(ext, src.end_lba)
print('--- gaps (data-track only)', gaps, 'total sectors', sum(g[1] for g in gaps))
# raw gaps incl audio
cur = ext[0][0] + ext[0][1]
print('--- raw gaps in volume')
for s, n, l in ext[1:]:
    if s > cur: print('gap', cur, s - cur, 'before', l)
    cur = max(cur, s + n)
print('last used end', cur)
# slack bytes in last sector of each file
slack = sum(D._nsec(r.size) * 2048 - r.size for r in files)
print('tail slack bytes total', slack)
# dir order of first file lbas
fl = sorted(files, key=lambda r: r.lba)
print('first files', [(r.path, r.lba) for r in fl[:5]])
print('last files', [(r.path, r.lba, D._nsec(r.size)) for r in fl[-5:]])
# directory sizes & slack
print('--- dirs')
for r in sorted(dirs, key=lambda r: r.lba):
    print('%7d size=%6d sectors=%d %s' % (r.lba, r.size, D._nsec(r.size), r.path))
