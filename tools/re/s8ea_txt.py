"""s8ea: show the text (A=hsk_full1 vs B=prop10c) of every differing range of a dump pair, NUL-split strings.

usage: s8ea_txt.py NAME LO HI [GAP]      (NAME like FLOW_PRG__EVENT.BIN; hex offsets)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(ROOT, 'build', 's8ea', 'dump')


def show(b, s, e):
    # extend to NUL boundaries
    while s > 0 and b[s - 1] != 0:
        s -= 1
    while e < len(b) and b[e] != 0:
        e += 1
    t = b[s:e]
    return s, t.decode('cp932', errors='replace').replace('\n', '\\n')


def main(argv):
    name = argv[1]
    lo, hi = int(argv[2], 16), int(argv[3], 16)
    gap = int(argv[4], 16) if len(argv) > 4 else 8
    a = open(os.path.join(D, 'A_' + name), 'rb').read()
    b = open(os.path.join(D, 'B_' + name), 'rb').read()
    hi = min(hi, len(a), len(b))
    rg = []
    for i in range(lo, hi):
        if a[i] != b[i]:
            if rg and i - rg[-1][1] <= gap:
                rg[-1][1] = i + 1
            else:
                rg.append([i, i + 1])
    for s, e in rg:
        sa, ta = show(a, s, e)
        sb, tb = show(b, s, e)
        print('%#x-%#x (%d)\n   A %s\n   B %s' % (s, e, e - s, ta[:300], tb[:300]))


if __name__ == '__main__':
    main(sys.argv)
