"""Exploration: twiddled-mip top level offset (smoothness vs offset)."""
import os
import sys
import glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bzlib  # noqa: E402
import pvr_scan  # noqa: E402


def twmap(n):
    bits = max(0, n.bit_length() - 1)
    a = np.arange(n)
    s = np.zeros(n, dtype=np.int64)
    for i in range(bits):
        s |= ((a >> i) & 1) << (2 * i)
    return (s[None, :] << 1) | s[:, None]


def rough(img):
    img = img.astype(np.float64)
    return float(np.abs(np.diff(img, axis=1)).mean() + np.abs(np.diff(img, axis=0)).mean())


def main():
    n = 128
    acc = {}
    cnt = 0
    for p in sorted([x for x in glob.glob('extracted/**/*', recursive=True) if os.path.isfile(x)]):
        d = open(p, 'rb').read()
        ms = bzlib.parse_archive(d)[0] if bzlib.parse_member(d, 0, False) else []
        blobs = [(m.name, m.extract()) for m in ms] if ms else [(p, d)]
        for name, b in blobs:
            recs = pvr_scan.parse_tbd(b, 0)
            if not recs:
                continue
            for r, plain, stored, method, err in pvr_scan.tbd_entries(b, 0, recs):
                if plain is None or r['dat'] != 2 or r['w'] != n:
                    continue
                w16 = np.frombuffer(plain, '<u2')
                tot = len(w16)
                for k in range(-3, 4):
                    off = tot - n * n + k
                    if off < 0 or off + n * n > tot:
                        # beyond the end: skip
                        continue
                    img = w16[off:off + n * n][twmap(n)]
                    # roughness on luminance-ish (4444 -> R,G,B nibble sum)
                    rr = ((img >> 8) & 15) + ((img >> 4) & 15) + (img & 15)
                    acc.setdefault(k, []).append(rough(rr))
                cnt += 1
    print('samples', cnt)
    for k in sorted(acc):
        print('offset rel to "last n*n words": %3d  roughness %.2f' % (k, float(np.mean(acc[k]))))


main()
