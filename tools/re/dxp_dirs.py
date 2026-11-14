"""Read-only: directory slack, path tables, PVD and IP.BIN TOC facts. usage: dxp_dirs.py"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
print('PVD vol id', pvd[40:72], 'sys id', pvd[8:40])
print('vol space', struct.unpack_from('<I', pvd, 80)[0], 'set size', struct.unpack_from('<H', pvd, 120)[0], 'block', struct.unpack_from('<H', pvd, 128)[0])
pts = struct.unpack_from('<I', pvd, 132)[0]
print('path table size', pts, 'L', struct.unpack_from('<I', pvd, 140)[0], 'Lopt', struct.unpack_from('<I', pvd, 144)[0], 'M', struct.unpack_from('>I', pvd, 148)[0], 'Mopt', struct.unpack_from('>I', pvd, 152)[0])
print('root rec', rl, rs)
print('dates', pvd[813:830], pvd[830:847])
dirs = [(rl, rs, '/')] + [(r.lba, r.size, r.path) for r in recs if r.isdir]
tot_free = 0
for lba, size, path in sorted(dirs):
    data = src.read(lba, size)
    pos = 0; used = 0; n = 0; last = 0
    while pos < len(data):
        l = data[pos]
        if l == 0:
            pos = (pos // 2048 + 1) * 2048; continue
        n += 1; used_end = pos + l; last = used_end; pos += l
    free = size - last
    # free bytes in the last sector only counts for appending records; show max record len
    tot_free += free
    print('%-14s lba=%d size=%5d recs=%3d last_rec_end=%5d free_tail=%4d' % (path, lba, size, n, last, free))
print('ISO names look like', [r.path for r in recs[:3]])
# raw name case/version
d = src.read(rl, rs)
pos = 0
while pos < 400:
    l = d[pos]
    if not l: break
    print('rec len', l, 'flags', d[pos+25], 'namelen', d[pos+32], d[pos+33:pos+33+d[pos+32]], 'sysuse', l - 33 - d[pos+32] - ((d[pos+32]+1)%2 ==1 and 0 or 0))
    pos += l
# path table
pt = src.read(struct.unpack_from('<I', pvd, 140)[0], pts)
i = 0; k = 1
while i < len(pt):
    nl = pt[i]; ext = struct.unpack_from('<I', pt, i + 2)[0]; par = struct.unpack_from('<H', pt, i + 6)[0]
    nm = pt[i + 8:i + 8 + nl]
    print('PT', k, ext, par, nm)
    i += 8 + nl + (nl & 1); k += 1
ip = src.read(45000, 16 * 2048)
print('IP meta', ip[:0x100])
print('TOC area 0x100..0x300:')
for off in range(0x100, 0x2a0, 4):
    v = struct.unpack_from('<I', ip, off)[0]
    if v not in (0, 0xffffffff): print('  %#05x %08x' % (off, v))
