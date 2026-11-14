"""mn6_fnstart.py REL OFFSET_HEX : file offset of the nearest function prologue (mov.l r14,@-r15 / mov.l r13,@-r15) at or before OFFSET.  Read only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402

d = MP.read_extracted(sys.argv[1])
o = int(sys.argv[2], 16)
for k in range(o & ~1, 0, -2):
    if d[k:k + 4] == bytes.fromhex('e62fd62f'):
        print('%#x' % k)
        break
