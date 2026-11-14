"""hsd_sk: run the GAME's own ZSARC walker (1ST_READ jump-table slot 0x3d4 -> 0x8c15a87c -> FUN_8c15a45a, mode 2 = find stored member and
return a pointer to its data) in tools/sh4sim.py on the member at a file offset of FLOW_PRG overlay of a trial disc.
usage: hsd_sk_walk.py DISC FILE HEXOFF ...   (e.g. bis_u1 FLOW_PRG/SCDRF.BIN 2ff38).  Prints the returned pointer (0 = NULL) and the logged messages.  Read-only."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D
import sh4sim

def rd(disc, rel):
    if disc == 'ORIG':
        return open(os.path.join(ROOT, 'extracted', rel), 'rb').read()
    src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    r = files['/' + rel.upper()]
    return src.read(r.lba, r.size)

K = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
WALK, PRINTF, STOP, X, STACK = 0x8c15a87c, 0x8c159f78, 0x8c000000, 0x8d000000, 0x8cfff000
d = rd(sys.argv[1], sys.argv[2])
for a in sys.argv[3:]:
    off = int(a, 16)
    m = sh4sim.Machine()
    m.load(0x8c010000, K)
    m.load(X, d[off:off + 0x4000])
    m.native = [(0x8c010000, 0x8c010000 + len(K))]
    msgs = []
    m.ext_ret[PRINTF] = lambda mm: msgs.append(mm.R[4])
    heap = [0x8d800000]                                  # the walker mallocs for header extensions: bump allocator stub

    def _alloc(mm):
        mm.R[0] = heap[0]
        heap[0] += (mm.R[4] + 0x40) & ~0x1f
    m.ext_ret[0x8c01ed3e] = _alloc
    m.ext_ret[0x8c01eaea] = lambda mm: None              # free
    m.R[4], m.R[5], m.R[6], m.R[15], m.PR = 0, X, 0, STACK, STOP
    steps = m.run(WALK, STOP, max_steps=5_000_000)
    r = m.R[0]
    print('%s %s @%s -> r0=%#x (%s) steps=%d logged=%d' % (sys.argv[1], sys.argv[2], a, r, 'NULL' if r == 0 else 'data +%#x' % (r - X), steps, len(msgs)))
    for p in msgs:
        s = bytes(m.rb(p + i) for i in range(40)).split(b'\0')[0]
        print('    msg:', s)
