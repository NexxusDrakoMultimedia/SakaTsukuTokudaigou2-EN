"""ovf: list 4-aligned file offsets that hold a given 32-bit value in an overlay.  usage: ovf_findlit.py OVERLAY HEXVALUE"""
import os, sys, struct
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', sys.argv[1] + '.BIN'), 'rb').read()
w = struct.pack('<I', int(sys.argv[2], 16))
print([hex(i) for i in range(0, len(d) - 3, 4) if d[i:i + 4] == w])
