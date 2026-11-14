"""svfmt_words.py OVERLAY HEXVAL... : every 4-aligned LE word == value (data pointers) plus bsr/bra targets."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load, entry_guess
d, base = load(sys.argv[1])
tg = set(int(x, 16) for x in sys.argv[2:])
for off in range(0, len(d) - 3, 2):
    v = struct.unpack_from('<I', d, off)[0]
    if v in tg and off % 4 == 0: print('word@%08x = %08x' % (base + off, v))
    w = struct.unpack_from('<H', d, off)[0]
    if (w >> 12) == 0xB:  # bsr
        disp = w & 0xFFF
        if disp & 0x800: disp -= 0x1000
        t = base + off + 4 + disp * 2
        if t in tg:
            e = entry_guess(d, off)
            print('bsr@%08x -> %08x  func~%s' % (base + off, t, '%08x' % (base + e) if e is not None else '?'))
