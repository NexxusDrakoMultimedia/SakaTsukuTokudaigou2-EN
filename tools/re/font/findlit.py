"""List aligned 32-bit literals equal to a value (or in a range) in an overlay: findlit.py OVERLAY.BIN hexvalue [hexhi]"""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from disov import load
img, r = load(sys.argv[1])
lo = int(sys.argv[2], 16)
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else lo
d = img.d
for o in range(0, len(d) - 3, 4):
    v = struct.unpack_from('<I', d, o)[0]
    if lo <= v <= hi:
        print('%08x: %08x' % (img.base + o, v))
