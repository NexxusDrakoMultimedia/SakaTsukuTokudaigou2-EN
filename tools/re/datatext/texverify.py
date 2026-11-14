"""Verify the TBD texture-bundle decoding over every bundle on the disc:
every record must decompress (bz/bzw per flag bits) to exactly the size implied by (datatype, w, h)
for the non-mipmapped types (twiddled/rect: w*h*2, VQ: 2048 + w*h/4, small VQ: codebook + w*h/4);
mipmapped types must be >= the top-level size.
python -I -X utf8 tools/re/datatext/texverify.py  -> prints counts, exits 1 on any mismatch
"""
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr


def expected(dt, w, h):
    if dt in (1, 9, 0xD):
        return w * h * 2, True
    if dt == 3:
        return 2048 + w * h // 4, True
    if dt == 0x10:
        nc = 16 if w <= 16 else 32 if w <= 32 else 128 if w <= 64 else 256
        return nc * 8 + w * h // 4, True
    if dt == 2:
        return w * h * 2, False
    if dt == 4:
        return 2048 + w * h // 4, False
    if dt == 0x11:
        nc = 16 if w <= 16 else 64 if w <= 32 else 256
        return nc * 8 + w * h // 4, False
    return None, False


stat = collections.Counter()
bad = []
for root in ('extracted', 'build/unpacked'):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn).replace(chr(92), '/')
            if 'BCAST' in p or fn.startswith('_') or p.startswith('extracted/FLOW_PRG') or p.startswith('extracted/SSONG'):
                continue
            if os.path.getsize(p) > 20_000_000:
                continue
            d = open(p, 'rb').read()
            if d[:4] in (b'GBIX', b'PVRT') or d[2:7] in (b'-nc--', b'-bz--', b'-bzw-'):
                continue
            recs = pvr.parse_tbd(d)
            if not recs:
                continue
            for i, r in enumerate(recs):
                stat['textures'] += 1
                stat['comp%d' % r['comp']] += 1
                try:
                    plain = pvr.tbd_plain(r)
                except Exception as e:
                    stat['decomp-error'] += 1
                    bad.append((p, i, 'decomp', str(e)))
                    continue
                exp, exact = expected(r['dt'], r['w'], r['h'])
                if exp is None:
                    stat['dt-unknown'] += 1
                    continue
                ok = len(plain) == exp if exact else len(plain) >= exp
                stat['size-ok' if ok else 'size-mismatch'] += 1
                if not ok:
                    bad.append((p, i, 'size', '%d vs %d dt=%d %dx%d' % (len(plain), exp, r['dt'], r['w'], r['h'])))
print(dict(stat))
for b in bad[:15]:
    print('BAD', b)
sys.exit(1 if bad else 0)
