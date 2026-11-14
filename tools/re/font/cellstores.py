"""For one overlay list every 'mov #0x3c,r0' (store of cells-per-line) site with the nearest preceding immediate loaded into the stored
register and the matching rows (0x3d) / advance (0x3e) / lineh (0x3f) / x(0x4a) stores in the following 40 instructions.
usage: cellstores.py OVERLAY.BIN"""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from disov import load


def s8(x):
    return x - 256 if x > 127 else x


def scan(name):
    img, r = load(name)
    base = img.base
    d = img.d
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    out = []
    for i, w in enumerate(W):
        if (w & 0xFF00) == 0xE000 and (w & 0xFF) == 0x3c:        # mov #60,r0
            got = {}
            for j in range(i + 1, min(i + 4, len(W))):
                v = W[j]
                if (v & 0xF00F) == 0x0004:                          # mov.b Rm,@(r0,Rn)
                    m = (v >> 4) & 15
                    for k in range(j - 1, max(j - 14, 0), -1):
                        u = W[k]
                        if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                            got['cells'] = s8(u & 0xFF)
                            break
                    else:
                        got['cells'] = '?'
                    break
            if not got:
                continue
            # look at the following instructions for other field stores
            fields = {}
            for k in range(i, min(i + 60, len(W))):
                if (W[k] & 0xFF00) == 0xE000 and (W[k] & 0xFF) in (0x3d, 0x3e, 0x3f, 0x45, 0x46):
                    f = W[k] & 0xFF
                    for j in range(k + 1, min(k + 4, len(W))):
                        v = W[j]
                        if (v & 0xF00F) == 0x0004:
                            m = (v >> 4) & 15
                            for q in range(j - 1, max(j - 14, 0), -1):
                                u = W[q]
                                if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                                    fields.setdefault(f, s8(u & 0xFF))
                                    break
                            break
            out.append((base + i * 2, got['cells'], fields))
    return out


if __name__ == '__main__':
    for a, c, f in scan(sys.argv[1]):
        print('%08x cells=%s rows=%s adv=%s lineh=%s flag45=%s size46=%s' % (a, c, f.get(0x3d), f.get(0x3e), f.get(0x3f), f.get(0x45), f.get(0x46)))
