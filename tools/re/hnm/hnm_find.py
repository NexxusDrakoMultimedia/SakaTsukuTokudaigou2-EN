"""Find 32-bit little-endian words equal to given values (hex) in HOMETOWN.BIN.  usage: hnm_find.py HEX..."""
import sys, os, struct
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
for a in sys.argv[1:]:
    v = int(a, 16)
    pat = struct.pack('<I', v)
    i = -1
    hits = []
    while True:
        i = d.find(pat, i + 4 if False else i + 1)
        if i < 0: break
        hits.append(hex(i))
    print(a, hits)
