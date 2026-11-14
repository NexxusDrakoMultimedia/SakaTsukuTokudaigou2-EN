"""svfmt_entries.py OVERLAY LO HI : guess function entries (prologue: pushes + sts.l pr,@-r15) in [LO,HI)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load
d, base = load(sys.argv[1]); lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16)
out = []
for off in range(lo - base, hi - base, 2):
    w = struct.unpack_from('<H', d, off)[0]
    if w == 0x4F22:
        k = off
        while k >= 2:
            p = struct.unpack_from('<H', d, k - 2)[0]
            if (p & 0xFF0F) == 0x2F06 or p in (0x4F02, 0x4F12) or (p & 0xFF0F) == 0x4F02:
                k -= 2
            else: break
        out.append(base + k)
print(','.join('%08x' % x for x in sorted(set(out))))
