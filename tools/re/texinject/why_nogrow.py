"""Why can't the members of a ZSARC container grow?  python -I -X utf8 tools/re/texinject/why_nogrow.py GAME/ALLLOGOS.BIN ..."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T  # noqa: E402

for rel in sys.argv[1:]:
    d = T._as_bytes(rel)
    ms, tail = T.zs_members(d)
    ok, why = T.zs_growable(d, ms, tail)
    print('%-28s members=%d tail=%#x len=%#x growable=%s %s' % (rel, len(ms), tail, len(d), ok, why))
    gaps = [b.offset - a.end_offset for a, b in zip(ms, ms[1:])]
    print('   gaps', sorted(set(gaps))[:10], 'last member end %#x' % (ms[-1].end_offset if ms else 0))
