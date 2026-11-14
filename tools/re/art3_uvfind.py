"""art3_uvfind.py - search overlays for atlas rectangle constants of PL_PT4 labels (u16 LE pairs / f32)."""
import glob, os, struct
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
pats = {}
for (x, y) in [(141, 273), (143, 337), (296, 272), (221, 288), (141, 304), (222, 418), (296, 305)]:
    pats['u16 %d,%d' % (x, y)] = struct.pack('<HH', x, y)
    pats['f32 %d/512' % x] = struct.pack('<f', x / 512.0)
files = glob.glob(os.path.join(root, 'extracted', 'FLOW_PRG', '*.BIN')) + [os.path.join(root, 'extracted', '1ST_READ.BIN')]
for f in files:
    d = open(f, 'rb').read()
    for k, p in pats.items():
        i = d.find(p)
        while i >= 0:
            print(os.path.basename(f), k, hex(i))
            i = d.find(p, i + 1)
