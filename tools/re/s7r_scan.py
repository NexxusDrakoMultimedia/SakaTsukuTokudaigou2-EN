"""s7r_scan FILE v1 v2 ... : offsets in FILE where all values appear as u16 LE (or u32 LE) within a 24 byte window, in any order."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
vals = [int(v) for v in sys.argv[2:]]
n = len(d)
for width, fmt in ((2, '<H'), (4, '<I')):
    hits = 0
    for o in range(0, n - 32, width):
        win = [struct.unpack_from(fmt, d, o + k * width)[0] for k in range(24 // width * 1)]
        if all(v in win for v in vals):
            print(width, hex(o), win[:12])
            hits += 1
            if hits > 30: break
