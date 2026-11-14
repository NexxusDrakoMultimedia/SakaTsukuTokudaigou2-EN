"""s8ha: read files back from a trial disc (read-only) and write them to a scratch directory.

usage: s8ha_extract.py DISC_DIR DISC_NAME OUT_DIR PATH...      e.g. build/trial s8e_notag out FLOW_PRG/EVENT.BIN 1ST_READ.BIN
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D   # noqa: E402

src = D.Source(sys.argv[1], sys.argv[2])
_p, _rl, _rs, recs = D.read_filesystem(src)
files = {r.path.upper(): r for r in recs if not r.isdir}
for p in sys.argv[4:]:
    r = files['/' + p.upper()]
    d = src.read(r.lba, r.size)
    dst = os.path.join(sys.argv[3], p.replace('/', '__'))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(d)
    print(p, len(d), dst)
