"""skh: find a 32-bit literal in 1ST_READ.BIN and every extracted overlay.  usage: skh_findlit.py HEXVALUE [HEXVALUE ...]  (prints file, file offset)"""
import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), os.path.join(ROOT, 'extracted', '2_DP.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
for v in sys.argv[1:]:
    pat = struct.pack('<I', int(v, 16))
    for f in files:
        d = open(f, 'rb').read()
        i = d.find(pat)
        offs = []
        while i >= 0:
            if i % 4 == 0:
                offs.append(i)
            i = d.find(pat, i + 1)
        if offs:
            print('%s %s: %s' % (v, os.path.relpath(f, ROOT), ' '.join('%#x' % o for o in offs[:12])))
