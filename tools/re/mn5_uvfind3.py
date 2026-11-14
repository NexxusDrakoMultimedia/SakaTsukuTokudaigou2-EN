"""mn5_uvfind3.py: look for any 32-bit / 16-bit packed encodings of header bar cells (Yr 198,36 / Mo 260,36 / Wk 296,36 / oku 462,266) in 1ST_READ + overlays."""
import os, sys, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))) + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'ATFIRST', '*.BIN'))) + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'GAME', '*')))
pats = {}
for n, (x, y) in {'yr': (198, 36), 'mo': (260, 36), 'wk': (296, 36), 'oku': (462, 266), 'man': (66, 141)}.items():
    pats[n + ' H,H'] = struct.pack('<2H', x, y)
    pats[n + ' h,h big'] = struct.pack('>2H', x, y)
    pats[n + ' i,i'] = struct.pack('<2i', x, y)
    pats[n + ' f,f px'] = struct.pack('<2f', float(x), float(y))
    pats[n + ' f,f /512'] = struct.pack('<2f', x / 512.0, y / 512.0)
    pats[n + ' f,f /256 (hw)'] = struct.pack('<2f', x / 256.0, y / 256.0)
for p in files:
    if os.path.isdir(p):
        continue
    d = open(p, 'rb').read()
    for n, pat in pats.items():
        i = d.find(pat)
        c = 0
        while i >= 0 and c < 3:
            print('%-30s %-18s off %x' % (os.path.relpath(p, ROOT), n, i)); c += 1
            i = d.find(pat, i + 1)
