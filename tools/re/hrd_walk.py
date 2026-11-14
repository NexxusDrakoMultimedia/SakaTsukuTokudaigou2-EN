"""hrd: what the game's ZSARC walker (FUN_8c15a45a, re-implemented in texinject.game_walk_zsarc) and the TBD list
builder (FUN_8c15a776 -> texinject.game_load_tbd) do with the stored member at OFFSET of a file, for several images.

usage: hrd_walk.py FILE OFFSET SPEC [SPEC ...]
  FILE ISO-style path (FLOW_PRG/SCDRF.BIN), OFFSET hex file offset of the member header (2ff38),
  SPEC as in hrd_members.py: orig | trial disc name | dir:PATH | ram:DUMP@HEXBASE
Read-only.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import texinject as T            # noqa: E402
import hrd_members as HM         # noqa: E402


def main(argv):
    path, off = argv[1], int(argv[2], 16)
    for spec in argv[3:]:
        d = HM.getter(spec)(path)
        try:
            members, end, why = T.game_walk_zsarc(d, off)
        except T.TexInjectError as e:
            print('%-40s walker FAILS: %s  -> the game gets NULL' % (spec[:40], e))
            continue
        ext, plain = members[0]
        recs = T.game_load_tbd(plain, 0)
        print('%-40s walker OK: %d member(s), stop %#x (%s); first member %d bytes sha1 %s; TBD list: %d record(s) %s'
              % (spec[:40], len(members), end, why, len(plain), hashlib.sha1(plain).hexdigest()[:10], len(recs),
                 [(type(r).__name__ if not isinstance(r, (tuple, list, dict)) else '') for r in recs][:0]))
        for r in recs:
            fmt, dt, w, h, st, data = r
            print('      pixfmt %d datatype %#x %dx%d stamp %#x payload %d bytes sha1 %s'
                  % (fmt, dt, w, h, st, len(data), hashlib.sha1(bytes(data)).hexdigest()[:10]))


if __name__ == '__main__':
    main(sys.argv)
