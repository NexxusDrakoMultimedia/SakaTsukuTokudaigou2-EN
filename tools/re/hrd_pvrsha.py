"""hrd: header fields and payload sha1 of PVR files.  usage: hrd_pvrsha.py FILE.pvr [...]   Read-only."""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T            # noqa: E402

for p in sys.argv[1:]:
    v = T.parse_pvr(open(p, 'rb').read())
    print('%s: gbix %s pixfmt %d datatype %#x %dx%d payload %d bytes sha1 %s'
          % (p, v.index, v.fmt, v.dt, v.w, v.h, len(v.payload), hashlib.sha1(v.payload).hexdigest()[:10]))
