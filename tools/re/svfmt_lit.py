"""svfmt_lit.py OVERLAY HEXADDR... : print 32-bit LE words and 16-bit halves at addresses; for each word that looks like an overlay/1ST_READ address, the cp932/ascii string there."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d, base = load(sys.argv[1])
fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
def rd(a, n):
    if base <= a < base + len(d): return d[a - base:a - base + n]
    if 0x8c010000 <= a < 0x8c010000 + len(fr): return fr[a - 0x8c010000:a - 0x8c010000 + n]
    return None
for x in sys.argv[2:]:
    a = int(x, 16)
    b = rd(a, 4)
    w = struct.unpack('<I', b)[0]; h = struct.unpack('<hh', b)
    s = ''
    r = rd(w, 40) if w >= 0x8c000000 else None
    if r:
        z = r.split(b'\0')[0]
        s = z.decode('cp932', 'replace') if all(c >= 32 for c in z) and z else ''
    print('%08x  w=%08x  h=%d,%d  str=%r' % (a, w, h[0], h[1], s))
