"""aln: for every call of a literal-loaded function (default strlen 0x8c014de4) in an address range, print the context
(the 3 instructions before the jsr and the 8 after), to see what the returned value is used for.

    python -I -X utf8 tools/re/aln_strlen_ctx.py OVERLAY START END [VALUE]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_dis as D  # noqa: E402
import aln_xref as X  # noqa: E402

name, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
val = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x8c014de4
d, base = D.load(name)
loads = [x for x in X.xrefs(d, val, base) if a <= x[0] - base < b]
for addr, pool, reg in loads:
    off = addr - base
    # find the jsr/jmp @reg after the load
    j = None
    for k in range(off, off + 40, 2):
        w = struct.unpack_from('<H', d, k)[0]
        if w == (0x400B | reg << 8) or w == (0x402B | reg << 8):
            j = k
            break
    print('=== load %08x pool %08x  jsr/jmp at %s' % (addr, pool, ('%08x' % (base + j)) if j else None))
    if j:
        print('\n'.join(D.listing(d, j - 6, j + 20, base)))
