"""hsd_sk: find 32-bit LE words 0x8cXXXXXX in FILE whose (word - base) equals each given target offset for any base in 0x8c010000..0x8d000000 step 0x1000.
usage: hsd_sk_ptr.py FILE HEXOFF ...  Read-only."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
ws = {}
for o in range(0, len(d) - 3, 4):
    w = struct.unpack_from('<I', d, o)[0]
    if 0x8c000000 <= w < 0x8d000000:
        ws.setdefault(w, []).append(o)
for a in sys.argv[2:]:
    t = int(a, 16)
    for base in range(0x8c010000, 0x8d000000, 0x1000):
        if base + t in ws:
            print('target %#x base %#x word %#x at %s' % (t, base, base + t, [hex(x) for x in ws[base + t]]))
