"""fw_wlit.py VALUE [VALUE ..] [--imm]: per overlay (FLOW_PRG, ATFIRST, 1ST_READ) count the PC-relative halfword loads
`mov.w @(disp,PC),Rn` whose literal equals VALUE (exact decode of every 0x9nDD word), i.e. code that uses VALUE as a 16-bit
struct offset / stride / size.  Also counts `mov #imm8,Rn` (0xEnII) when VALUE fits in a signed byte and --imm is given.
Read-only helper of the field-width study.  Output: total files/sites, then per file counts."""
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
imm = '--imm' in sys.argv
vals = [int(a, 0) for a in args]
roots = [('extracted/FLOW_PRG', 0), ('extracted/ATFIRST', 0), ('extracted', 0)]
res = {v: {} for v in vals}
paths = []
for sub in ('extracted/FLOW_PRG', 'extracted/ATFIRST'):
    for n in sorted(os.listdir(sub)):
        if n.endswith('.BIN'):
            paths.append(os.path.join(sub, n))
paths.append('extracted/1ST_READ.BIN')
for p in paths:
    d = open(p, 'rb').read()
    for a in range(0, len(d) - 1, 2):
        x = d[a] | d[a + 1] << 8
        if x >> 12 == 0x9:
            t = a + 4 + 2 * (x & 0xFF)
            if t + 1 < len(d):
                lv = d[t] | d[t + 1] << 8
                for v in vals:
                    if lv == v:
                        res[v][p] = res[v].get(p, 0) + 1
        elif imm and x >> 12 == 0xE:
            b = x & 0xFF
            sb = b - 256 if b & 0x80 else b
            for v in vals:
                if sb == v:
                    res[v][p] = res[v].get(p, 0) + 1
for v in vals:
    r = res[v]
    print('value %#x (%d): %d sites in %d files' % (v, v, sum(r.values()), len(r)))
    print('   ', ' '.join('%s:%d' % (os.path.basename(k).replace('.BIN', ''), c) for k, c in sorted(r.items(), key=lambda kv: -kv[1])[:40]))
