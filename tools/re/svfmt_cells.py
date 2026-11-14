"""svfmt_cells.py : histogram of immediate values stored into a text-window field +0x3c (cells per line):  mov #0x3c,r0 ... mov.b Rm,@(r0,Rn)
with Rm loaded by `mov #imm,Rm` just before.  Per overlay and total; shows whether narrow (e.g. 7-cell) label windows exist outside MEETING."""
import sys, os, struct, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tot = collections.Counter(); per = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))):
    d = open(f, 'rb').read(); n = len(d); c = collections.Counter()
    H = struct.unpack_from('<%dH' % (n // 2), d, 0)
    for i, w in enumerate(H):
        if w != 0xE03C: continue
        for j in range(i + 1, min(i + 4, len(H))):
            x = H[j]
            if (x & 0xF00F) == 0x0004:  # mov.b Rm,@(r0,Rn)
                m = (x >> 4) & 15
                for k in range(max(0, i - 6), j):
                    y = H[k]
                    if (y & 0xF000) == 0xE000 and ((y >> 8) & 15) == m:
                        c[y & 0xFF] += 1
                break
    per[os.path.basename(f)[:-4]] = c; tot.update(c)
print('total', sorted(tot.items()))
for k in (5, 6, 7, 8, 9, 10):
    print('cells', k, ': overlays', [n for n, c in per.items() if c[k]][:12], 'sites', tot[k])
