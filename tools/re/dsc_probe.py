"""dsc_probe: read-only facts about the ISO9660 metadata that the dsc disc tooling relies on.
usage: python -I -X utf8 tools/re/dsc_probe.py
Checks on the ORIGINAL disc: directory record packing, record order key, path table order key, duplicate groups."""
import os, sys, struct, hashlib, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D

src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
dirs = [('/', rl, rs)] + [(r.path, r.lba, r.size) for r in recs if r.isdir]


def parse(data):
    out, pos = [], 0
    while pos < len(data):
        l = data[pos]
        if l == 0:
            pos = (pos // 2048 + 1) * 2048
            continue
        out.append((pos, data[pos:pos + l]))
        pos += l
    return out


# 1. repacking equals the original; sorted by which key
for path, lba, size in dirs:
    data = src.read(lba, size)
    rr = parse(data)
    out = bytearray()
    for _, rec in rr:
        if (len(out) % 2048) + len(rec) > 2048:
            out += bytes(2048 - len(out) % 2048)
        out += rec
    out += bytes(size - len(out))
    same = bytes(out) == data
    names = [rec[33:33 + rec[32]] for _, rec in rr[2:]]
    s_full = names == sorted(names)
    s_nov = [n.split(b';')[0] for n in names]
    print('%-14s %4d recs repack-equal=%s sorted(full)=%s sorted(no ver)=%s' % (
        path, len(rr), same, s_full, s_nov == sorted(s_nov)))
# 2. path table: regenerate
pts, = struct.unpack_from('<I', pvd, 132)
for off, e in ((140, '<'), (148, '>')):
    pl, = struct.unpack_from(e + 'I', pvd, off)
    print('PT at', pl, 'size', pts)
    print(src.read(pl, pts)[:80].hex())
by = collections.defaultdict(list)
files = [r for r in recs if not r.isdir and r.size]
for r in files:
    by[(r.size, hashlib.sha1(src.read(r.lba, r.size)).hexdigest())].append(r.path)
g = [v for v in by.values() if len(v) > 1]
print('dup groups', len(g), 'extra copies', sum(len(v) - 1 for v in g),
      'sectors', sum((D._nsec(k[0]) * (len(v) - 1)) for k, v in by.items() if len(v) > 1))
for v in g:
    print('  ', v)
