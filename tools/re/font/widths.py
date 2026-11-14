"""Derive the 256-byte advance table from the half-width glyph block of a FONT.BIN.

    python -I -X utf8 tools/re/font/widths.py [FONT.BIN]        (default: extracted/FONT.BIN) -> prints the table summary

table[b] = advance in pixels for the single byte b (indexed by the low byte of the code word the string compiler
produces: 0x8000 | 0x4000? | b).  Glyph art is left aligned in the 12-px cell, so advance = right-most ink column + 1 + gap.
Bytes that have no half-width glyph (0x00-0x1f, 0x80-0x9f) get 0 = "use 12" (cave fallback).  Index 0x20 (space) gets `space`.
Table index 0 is the character used for code 0x2020 (the string compiler's space cell): the cave is called with
r4 = 0x8000, so table[0] must hold the SPACE width (set below), not table[0x20].
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import font as F   # noqa: E402


def ink_right(g, paper=15, thresh=15):
    """right-most column (0..11) that has a pixel < thresh in a 12x24 4 bpp glyph (6 bytes per row), or -1."""
    best = -1
    for r in range(24):
        row = g[r * 6:(r + 1) * 6]
        for c in range(12):
            nib = (row[c >> 1] >> 4) if c % 2 == 0 else (row[c >> 1] & 15)
            if nib < thresh:
                best = max(best, c)
    return best


def make_table(font, gap=1, space=6, minw=2, maxw=12):
    half = font.half()
    t = bytearray(256)
    for b in list(range(0x21, 0x80)) + list(range(0xA0, 0xE0)):
        i = F.half_index(b)
        r = ink_right(half[i])
        t[b] = 0 if r < 0 else max(minw, min(maxw, r + 1 + gap))
    t[0x20] = space
    t[0x00] = space          # code 0x2020 reaches the cave as 0x8000 -> index 0
    return bytes(t)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'extracted', 'FONT.BIN')
    f = F.Font.load(path)
    t = make_table(f)
    from collections import Counter
    c = Counter(t[b] for b in range(0x21, 0x7f))
    print('ASCII 0x21-0x7e advance histogram (gap=1):', dict(sorted(c.items())))
    print('mean %.2f px (fixed font: 12)' % (sum(t[b] for b in range(0x21, 0x7f)) / 94))
    print(' '.join('%02x:%d' % (b, t[b]) for b in range(0x20, 0x7f)))
