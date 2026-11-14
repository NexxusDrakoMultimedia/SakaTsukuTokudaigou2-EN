"""tdl: how much of a repainted VQ texture is the original's codebook / index table (derived-pixel measurement)."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texdelta as T   # noqa: E402
import texinject       # noqa: E402

orig = T.Originals(T.DEF_EXTRACTED)
tot = [0, 0, 0, 0, 0]
for full in T._walk(T.DEF_TEXTURES, '.pvr'):
    rel = T._rel(full, T.DEF_TEXTURES)
    cont, tid = T.split_container(rel.split('/'), T.DEF_EXTRACTED)
    src = orig.texture(cont, tid[:-4])
    tgt = open(full, 'rb').read()
    a, b = texinject.parse_pvr(src), texinject.parse_pvr(tgt)
    if a.dt not in (3, 4, 0x10, 0x11):
        continue
    nc = 256 if a.dt in (3, 4) else {16: 16, 32: 32}.get(a.w, 128 if a.w <= 64 else 256)
    cb = nc * 8
    oc = {a.payload[i:i + 8] for i in range(0, cb, 8)}
    nent = [b.payload[i:i + 8] for i in range(0, cb, 8)]
    same_ent = sum(1 for e in nent if e in oc)
    same_at = sum(1 for i in range(0, cb, 8) if b.payload[i:i + 8] == a.payload[i:i + 8])
    ia, ib = a.payload[cb:], b.payload[cb:]
    idx_same = sum(1 for x, y in zip(ia, ib) if x == y)
    print('%-52s fmt%d dt%d %dx%d  codebook entries equal to ANY original entry %3d/%d, at same slot %3d; index bytes equal %5d/%d' % (
        rel, a.fmt, a.dt, a.w, a.h, same_ent, nc, same_at, idx_same, len(ia)))
    tot[0] += 1
    tot[1] += same_ent
    tot[2] += nc
    tot[3] += idx_same
    tot[4] += len(ia)
print('VQ textures %d: codebook entries equal to an original one %d/%d, index bytes equal %d/%d' % tuple(tot))
