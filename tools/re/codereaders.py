"""codereaders.py SOURCE HEXOFF [N] : find literal-pool words that equal base+HEXOFF (aligned) and the
`mov.l @(disp,PC),Rn` instructions that load them, print N instructions around each load (tools/sh4asm.dis).
Evidence for 'which code reads this table' in docs/uncovered-text.md.  Static only (no emulation)."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T
import sh4asm

src = sys.argv[1]
target_off = int(sys.argv[2], 16)
N = int(sys.argv[3]) if len(sys.argv) > 3 else 10
img = T.load_image(src)
d, base = img.data, img.base
tgt = base + target_off
nwords = len(d) // 4
words = struct.unpack('<%dI' % nwords, d[:nwords * 4])
lits = [i * 4 for i, w in enumerate(words) if w == tgt]
print('%s base %#x  words == %#x at %s' % (src, base, tgt, [hex(x) for x in lits]))
for L in lits:
    # find mov.l @(disp,PC),Rn : 0xD<n><disp8>, EA = (A & ~3) + 4 + 4*disp ; A = addr of instruction (file offset here)
    users = []
    lo = max(0, L - 4 * 256 - 8)
    for A in range(lo, L, 2):
        w = d[A] | d[A + 1] << 8
        if w >> 12 == 0xD:
            ea = (A & ~3) + 4 + 4 * (w & 0xFF)
            if ea == L:
                users.append(A)
    print(' literal @%#x loaded by instructions at %s' % (L, [hex(u) for u in users]))
    for A in users[:3]:
        print(sh4asm.listing(d[max(0, A - 16):A + 2 * N], base + max(0, A - 16)))
