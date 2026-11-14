"""aln: find the "x = anchor - 12 * len" idiom (cell-count alignment) in every extracted FLOW_PRG overlay.

    python -I -X utf8 tools/re/aln_scan12.py [OVERLAY ...]

The compiler expands `r * 12` into a copy, a shll (x2), an add (x3) and a shll2 (x12) that may be interleaved with other
instructions: mov rB,rA' ; shll rA ; add rB,rA ; ... ; shll2 rA.  Hits are filtered to those that store a halfword at window offset 74
(`mov #74,r0`, the text origin x) within 40 instructions: the alignment idiom.  Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIR = os.path.join(ROOT, 'extracted', 'FLOW_PRG')


def words(d):
    return struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])


def scan(ws):
    hits = []
    for i in range(len(ws) - 10):
        w = ws[i]
        if w >> 12 == 6 and (w & 15) == 3:       # mov rm,rn
            n = (w >> 8) & 15
            m = (w >> 4) & 15                    # r_m copy source = the value, r_n = its copy
            a, b = m, n                           # a: value reg (gets shifted), b: copy
            win = ws[i + 1:i + 9]
            if (0x4000 | a << 8) in win and (0x4008 | a << 8) in win and (0x300C | a << 8 | b << 4) in win:
                hits.append(i * 2)
    return hits


def near_xstore(ws, off, span=40):
    i = off // 2
    return any(ws[j] >> 12 == 0xE and (ws[j] & 0xFF) == 0x4A for j in range(i, min(len(ws), i + span)))


def main():
    names = sys.argv[1:] or sorted(n for n in os.listdir(DIR) if n.endswith('.BIN'))
    tot = 0
    allh = 0
    for n in names:
        if not n.endswith('.BIN'):
            n += '.BIN'
        ws = words(open(os.path.join(DIR, n), 'rb').read())
        hits = scan(ws)
        xs = [h for h in hits if near_xstore(ws, h)]
        tot += len(xs)
        allh += len(hits)
        if xs:
            print('%-14s x12 hits %3d  with x-store nearby %3d  %s' % (n, len(hits), len(xs), ' '.join('%x' % h for h in xs[:14])))
    print('total x12 %d, with x-store nearby %d' % (allh, tot))


if __name__ == '__main__':
    main()
