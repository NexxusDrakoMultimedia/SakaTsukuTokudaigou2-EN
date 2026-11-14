"""mn5_uvfind2.py: search for normalised float UV pairs (u,v) of the header bar unit cells in all extracted code/data files."""
import os, sys, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cells = {'oku(462,266)': (462, 266), 'oku end(492,298)': (492, 298), 'man(66,141)': (66, 141), 'man end(115,165)': (115, 165), 'digits row(305,430)': (305, 430)}
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))) + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'ATFIRST', '*.BIN')))
for p in files:
    d = open(p, 'rb').read()
    for n, (x, y) in cells.items():
        for scale in (512.0,):
            pat = struct.pack('<2f', x / scale, y / scale)
            i = d.find(pat)
            while i >= 0:
                print('%-26s %-22s off %x' % (os.path.relpath(p, ROOT), n, i))
                i = d.find(pat, i + 1)
