"""hex dump of HOMETOWN.BIN: hnm_hex.py OFFSET LEN [w]  (w = words)"""
import sys, os, struct
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
off = int(sys.argv[1], 16); n = int(sys.argv[2], 16)
if len(sys.argv) > 3:
    for i in range(off, off + n, 4):
        print('%x: %08x' % (i, struct.unpack_from('<I', d, i)[0]))
else:
    for i in range(off, off + n, 16):
        c = d[i:i+16]
        print('%x: %s  %s' % (i, c.hex(' '), ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)))
