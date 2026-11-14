"""svfmt_xrange.py OVERLAY LO HI : pc-relative literal loads whose value lies in [LO,HI] (hex virtual addresses)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load, entry_guess
d, base = load(sys.argv[1]); lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16)
for off in range(0, len(d) - 1, 2):
    w = struct.unpack_from('<H', d, off)[0]
    if (w >> 12) != 0xD: continue
    ea = ((base + off + 4) & ~3) + (w & 0xFF) * 4; eo = ea - base
    if not (0 <= eo < len(d) - 3): continue
    v = struct.unpack_from('<I', d, eo)[0]
    if lo <= v <= hi:
        e = entry_guess(d, off)
        print('%08x r%d <- %08x  lit@%08x func~%s' % (base + off, (w >> 8) & 15, v, ea, '%08x' % (base + e) if e is not None else '?'))
