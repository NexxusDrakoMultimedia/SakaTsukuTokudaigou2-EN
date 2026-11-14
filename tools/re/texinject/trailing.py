"""List whole-file TBD bundles whose last record is followed by more than 3 bytes after its end token.
python -I -X utf8 tools/re/texinject/trailing.py"""
import os
import sys
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import census     # noqa: E402
import analyze_tbd as A  # noqa: E402

ext = os.path.join(ROOT, 'extracted')
n_files = 0
for root, dirs, files in os.walk(ext):
    dirs.sort()
    for fn in sorted(files):
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, ext).replace('\\', '/')
        if fn in ('BCAST.BIN', '_filelist.tsv'):
            continue
        d = open(p, 'rb').read()
        n = census.tbd_ok(d)
        if not n:
            continue
        n_files += 1
        f, wh, off, stp = struct.unpack_from('<IIII', d, 4 + 16 * (n - 1))
        comp = f >> 30
        blk = d[off:]
        if comp == 2:
            c = A.consumed_bz(blk)
        elif comp == 1:
            c = A.consumed_bzw(blk)
        else:
            continue
        if c is not None and len(blk) - c > 3:
            tz = blk[c:]
            print('%-28s n=%d last comp=%d size=%d trailing=%d zero=%s' % (rel, n, comp, len(d), len(tz), not any(tz)))
print('whole-file bundles', n_files)
