"""mn5_uvfind.py: search extracted overlays + 1ST_READ for the sprite UV rectangles of the header bar unit cells (u16 / float patterns)."""
import os, sys, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pats = {
 'oku u16 x,y,w,h': struct.pack('<4H', 462, 266, 30, 32),
 'oku u16 x,y': struct.pack('<2H', 462, 266),
 'man u16 x,y,w,h': struct.pack('<4H', 66, 141, 49, 24),
 'man u16 x,y': struct.pack('<2H', 66, 141),
 'oku f 462,266': struct.pack('<2f', 462.0, 266.0),
 'man f 66,141': struct.pack('<2f', 66.0, 141.0),
}
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))) + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'ATFIRST', '*.BIN')))
for p in files:
    d = open(p, 'rb').read()
    for n, pat in pats.items():
        i = 0
        c = 0
        while True:
            i = d.find(pat, i)
            if i < 0:
                break
            if c < 4:
                print('%-30s %-26s off %x' % (os.path.relpath(p, ROOT), n, i))
            c += 1
            i += 1
