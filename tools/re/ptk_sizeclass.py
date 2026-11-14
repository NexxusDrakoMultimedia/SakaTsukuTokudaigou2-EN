"""Read-only: how many overlay sites store the window 'size class' (+0x46) and what do they store, next to the window
geometry stores (+0x3c cells, +0x3e advance).  Evidence for docs/expansion/patch-toolkit.md (small-font mode).

    python -I -X utf8 tools/re/ptk_sizeclass.py

Pattern: mov #FIELD,r0 ; (<=3 insns) ; mov.b Rm,@(r0,Rn)   and the nearest preceding  mov #imm,Rm  (<=12 insns back).
FIELD 0x46 = size class (0 = 12x24 half glyph, 1 = 16x32, 2 = 8x16), 0x3e = advance, 0x3c = cells per line.
"""
import collections
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIELDS = {0x3C: 'cells', 0x3E: 'advance', 0x46: 'sizeclass', 0x3F: 'lineh'}


def s8(x):
    return x - 256 if x > 127 else x


def scan(d):
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    out = []
    for i, w in enumerate(W):
        if (w & 0xFF00) == 0xE000 and (w & 0xFF) in FIELDS:
            for j in range(i + 1, min(i + 4, len(W))):
                v = W[j]
                if (v & 0xF00F) == 0x0004:
                    m = (v >> 4) & 15
                    val = '?'
                    for k in range(j - 1, max(j - 12, 0), -1):
                        u = W[k]
                        if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                            val = s8(u & 0xFF)
                            break
                    out.append((i * 2, w & 0xFF, val))
                    break
    return out


def main():
    hooks = os.path.join(ROOT, 'tools', 're', 'font', 'hooksites.tsv')
    names = []
    for ln in open(hooks, encoding='utf8').read().splitlines()[1:]:
        c = ln.split('\t')
        if c[2] == 'A':
            names.append((c[1], c[0]))
    hist = {f: collections.Counter() for f in FIELDS}
    files = collections.defaultdict(set)
    for dr, n in names:
        d = open(os.path.join(ROOT, 'extracted', dr, n), 'rb').read()
        for off, f, val in scan(d):
            hist[f][val] += 1
            files[(f, val)].add(n)
    for f in FIELDS:
        print('+%#x %-9s %s' % (f, FIELDS[f], dict(sorted(hist[f].items(), key=lambda x: str(x[0])))))
    print('overlays with a size-class store: %d  ->  %s' % (len({n for (f, v), s in files.items() if f == 0x46 for n in s}),
                                                          sorted({n for (f, v), s in files.items() if f == 0x46 for n in s})))
    for (f, v), s in sorted(files.items(), key=lambda x: str(x)):
        if f == 0x46:
            print('  sizeclass', v, sorted(s))
    print('overlays storing cells=17: %d, cells=20: %d, advance=16: %d' % (len(files[(0x3C, 17)]), len(files[(0x3C, 20)]), len(files[(0x3E, 16)])))


if __name__ == '__main__':
    main()
