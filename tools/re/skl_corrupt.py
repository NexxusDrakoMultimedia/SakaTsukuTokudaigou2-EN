# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_corrupt: prepare scratch copies of extracted/ with one corrupted byte / a missing file / a non-cp932 string.
   skl_corrupt.py DEST   -> DEST/flip (1 byte flipped inside FLOW_PRG/MEETING.BIN string 3f204), DEST/missing (a file removed)
Only copies out of extracted/ (read only) into DEST under build/."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dest = os.path.abspath(sys.argv[1])
assert os.path.commonpath([dest, os.path.join(ROOT, 'build')]) == os.path.join(ROOT, 'build')
src = os.path.join(ROOT, 'extracted')
for name in ('flip', 'missing'):
    shutil.copytree(src, os.path.join(dest, name))
p = os.path.join(dest, 'flip', 'FLOW_PRG', 'MEETING.BIN')
b = bytearray(open(p, 'rb').read())
print('byte at 3f204 before:', hex(b[0x3f204]))
b[0x3f204 + 2] ^= 0x01
open(p, 'wb').write(b)
os.remove(os.path.join(dest, 'missing', 'FLOW_PRG', 'MEETING.BIN'))
print('done')
