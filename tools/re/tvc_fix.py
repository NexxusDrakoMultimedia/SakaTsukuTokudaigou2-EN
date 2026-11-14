"""tvc_fix.py : replace the raw NUL line in tools/moneypatch.py by readable text."""
import os
p = 'tools/moneypatch.py'
d = open(p, 'rb').read()
bs = bytes([92])
bad = b"NOP_WORD = b'\t\x00'"
good = b"NOP_WORD = bytes((9, 0))"
assert bad in d
d = d.replace(bad, good)
open(p + '.tmp', 'wb').write(d)
os.replace(p + '.tmp', p)
