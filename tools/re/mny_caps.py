"""mny_caps.py : look for money-cap constants (units of 10,000 yen) in the extracted code: 32-bit literals 99999999, 9999999, 999999,
999999999, 99999, 9999 (and 10^k) aligned in literal pools of FLOW_PRG overlays / 1ST_READ.BIN.   python -I -X utf8 tools/re/mny_caps.py"""
import glob
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP

CONST = {}
for e in range(4, 10):
    CONST[10 ** e - 1] = '10^%d-1' % e
    CONST[10 ** e] = '10^%d' % e
files = ['1ST_READ.BIN'] + MP.overlay_paths()
hits = {}
for rel in files:
    d = MP.read_extracted(rel)
    for off in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, off)[0]
        if v in CONST and v >= 99999:
            hits.setdefault(CONST[v], []).append((rel, off))
for k in sorted(hits):
    xs = hits[k]
    print('%-8s %4d hits; files: %s' % (k, len(xs), ', '.join(sorted({r.split('/')[-1] for r, _ in xs})[:14])))
