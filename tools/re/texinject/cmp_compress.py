"""How does tools/bzlib.py's greedy encoder compare to the original encoder on real texture data?

    python -I -X utf8 tools/re/texinject/cmp_compress.py [N]   (N = max records, default 60)
Reports, for compressed TBD records (bz and bzw), the packed size of the original stream vs bzlib.compress and the
fraction where ours is <= original (the condition for an exact-size, in-place replacement)."""
import os
import sys
import struct
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import bzlib      # noqa: E402
import census     # noqa: E402
import analyze_tbd as A  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
ext = os.path.join(ROOT, 'extracted')
rows = []
t0 = time.time()
for sub in ('ETC_DATA', 'ATFIRST', 'TRAINING', 'NEWS'):
    for fn in sorted(os.listdir(os.path.join(ext, sub))):
        p = os.path.join(ext, sub, fn)
        d = open(p, 'rb').read()
        n = census.tbd_ok(d)
        if not n:
            continue
        offs = [struct.unpack_from('<I', d, 4 + 16 * i + 8)[0] for i in range(n)]
        for i in range(n):
            f = struct.unpack_from('<I', d, 4 + 16 * i)[0]
            comp = f >> 30
            if comp not in (1, 2):
                continue
            end = offs[i + 1] if i + 1 < n else len(d)
            blk = d[offs[i]:end]
            if comp == 2:
                c = A.consumed_bz(blk)
                plain = bzlib.decompress_bz(blk[:c])
                ours = bzlib.compress_bz(plain)
            else:
                c = A.consumed_bzw(blk)
                plain = bzlib.decompress_bzw(blk[:c])
                ours = bzlib.compress_bzw(plain)
            rows.append((sub + '/' + fn, i, comp, len(plain), c, len(ours)))
            if len(rows) >= N:
                break
        if len(rows) >= N:
            break
    if len(rows) >= N:
        break
ok = sum(1 for r in rows if r[5] <= r[4])
print('records', len(rows), 'ours<=orig', ok, 'time %.1fs' % (time.time() - t0))
for r in rows[:25]:
    print(r, '%+.2f%%' % (100.0 * (r[5] - r[4]) / r[4]))
tot_o = sum(r[4] for r in rows)
tot_n = sum(r[5] for r in rows)
print('total orig', tot_o, 'ours', tot_n, '%+.2f%%' % (100.0 * (tot_n - tot_o) / tot_o))
