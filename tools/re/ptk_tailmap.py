"""Read-only: zero-run map of the 1ST_READ.BIN tail (0x8c299400..0x8c2b0000) and of the big .text/data holes, and the
bytes the existing font + money patches claim (tools/fontpatch.py, tools/moneypatch.py).

    python -I -X utf8 tools/re/ptk_tailmap.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
BASE = 0x8C010000


def runs(d, lo, hi, minlen):
    out = []
    i = lo
    while i < hi:
        if d[i] == 0:
            j = i
            while j < hi and d[j] == 0:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def main():
    d = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    print('1ST_READ.BIN size %d  = %d sectors; ends at %#x' % (len(d), len(d) // 2048, BASE + len(d)))
    lo, hi = 0x8C299400 - BASE, 0x8C2B0000 - BASE
    print('tail 0x8c299400..0x8c2b0000 zero runs >= 64 B:')
    for a, b in runs(d, lo, hi, 64):
        print('   %#x..%#x  %d bytes' % (BASE + a, BASE + b, b - a))
    print('tail first non-zero byte after 0x8c299400:', hex(BASE + next(i for i in range(lo, hi) if d[i])))
    tot = 0
    n = 0
    for a, b in runs(d, 0, 0x2A0000, 4096):
        tot += b - a
        n += 1
    print('zero runs >= 4 KiB inside the first 0x2a0000 bytes: %d runs, %d bytes total' % (n, tot))
    import fontpatch
    import moneypatch
    print('font patch claims  %#x..%#x (cave) + table at %#x (256 B)' % (fontpatch.PLACEMENTS['tail'][0], fontpatch.PLACEMENTS['tail'][0] + fontpatch.RESERVE, fontpatch.PLACEMENTS['tail'][1]))
    print('money patch cave at %#x, reserve %#x B, cave bytes %d' % (moneypatch.CAVE_ADDR, moneypatch.RESERVE, len(moneypatch.cave_bytes())))


if __name__ == '__main__':
    main()
