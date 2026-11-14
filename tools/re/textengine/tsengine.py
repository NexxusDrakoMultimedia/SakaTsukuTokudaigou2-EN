"""tsengine - Python model of the game's "tsString" text window library
(textengine agent; see docs/text-engine.md for the decompiled evidence).

Every FLOW_PRG overlay that shows text (104 of 114) carries its own copy of this
library; the glyph back end (SJIS -> glyph index, glyph blit) lives in 1ST_READ.BIN.

Code units (u16) produced from a string  [overlay FUN_8c2ddeea, MEETING.BIN addr]:
    bit 0x2000   control code (nothing drawn): newline 0x200a, space 0x2020 (half cell),
                 0x2010 colour reset, 0x2011..0x2019 colour W,R,B,Y,G,M,P,K,O, 0x2030+n style
    bit 0x8000   half-width glyph (12x24, advance = advance/2)
    bit 0x4000   "may hang over the last cell" (kinsoku) flag
    else         full-width glyph index (0..3647) into FONT.BIN

Everything here is derived from decompiled code and was NOT validated against a
running game (no emulator available) - see docs/text-engine.md for PROVEN/INFERRED.
"""
import re

# kinsoku tables read from MEETING.BIN (0x8c374a04 / 0x8c374a39)
HANG_FULL = "、。」ー…？ぁぅぇぉぃっゃゅょァィゥェォャュョッヵヶ"   # MEETING.BIN 0x8c374a04, exact
HANG_HALF = bytes([0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa7, 0xa8, 0xa9, 0xaa,
                   0xab, 0xac, 0xad, 0xae, 0xaf, 0xb0])
COLOUR_LETTERS = b"WRBYGMPKO"      # "@R/" etc: code 0x2000|(index+0x10), index 1..9


def sjis_to_glyph(code):
    """1ST_READ FUN_8c15e7a0 (u16 SJIS code -> FONT.BIN glyph index, 0x17 = missing).
    Codes > 0x9890 only exist for 51 hand-picked kanji (table 0x8c169f04, indices
    0xdca..0xdfc); that table is not modelled here (returns 0x17)."""
    hi, lo = code >> 8, code & 0xff
    if code > 0x9890:
        return 0x17
    if hi == 0x88:
        idx = 0x196 + lo
    elif hi > 0x88:
        idx = (hi - 0x89) * 188 + 0x293 + (lo - 0x41 if lo >= 0x7f else lo - 0x40)
    else:
        idx = (hi - 0x81) * 188 + (lo - 0x41 if lo >= 0x7f else lo - 0x40)
    return idx if 0 <= idx < 3648 else 0x17


def is_lead(b):
    """FUN_8c2ddeea: lead byte test = not ((b < 0x80 or b >= 0xa0) and b < 0xe0)."""
    return not ((b < 0x80 or b >= 0xa0) and b < 0xe0)


def convert(data, raw=False):
    """bytes (after %/# expansion) -> list of u16 codes, like overlay FUN_8c2ddeea.
    raw=True is the window's "param_4/param_3 != 0" mode where '=' '@' are literal."""
    out = []
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if b == 0:
            break
        nxt = data[i + 1] if i + 1 < n else 0
        nxt2 = data[i + 2] if i + 2 < n else 0
        if b == 0x3d and not raw:                      # '='
            if nxt != 0 and nxt2 == 0x2f:              # "=X/" with X in W,K,I -> 1,2,3
                k = {0x57: 1, 0x4b: 2, 0x49: 3}.get(nxt, 0)   # (FUN_8c2ddeaa uses a helper fn;
                out.append(0x2000 | (0x30 + k)); i += 3        #  upper-casing assumed)
            else:
                out.append(0x2030); i += 1             # '=' alone = style 0, nothing printed
        elif b == 0x40 and not raw:                    # '@'
            if nxt != 0 and nxt2 == 0x2f:              # "@X/"
                k = COLOUR_LETTERS.find(bytes([nxt]))
                if k >= 0:
                    out.append(0x2000 | (k + 1 + 0x10))
                i += 3
            else:
                out.append(0x2010); i += 1             # '@' alone = colour reset
        elif b < 0x21:
            out.append(0x2000 | b); i += 1             # includes 0x0a newline, 0x20 space
        elif not is_lead(b):
            f = 0x4000 if b in HANG_HALF else 0
            out.append(b | f | 0x8000); i += 1
        else:
            if nxt == 0:
                i += 1; continue
            sj = (b << 8) | nxt
            g = sjis_to_glyph(sj)
            try:
                ch = bytes([b, nxt]).decode('cp932')
            except UnicodeDecodeError:
                ch = ''
            if g != 0x17 and ch and ch in HANG_FULL:
                g |= 0x4000
            out.append(g); i += 2
    return out


def layout(codes, cells, rows=None, last_cell_free=True):
    """Model of overlay FUN_8c2de294.  cells = window byte +0x3c (chars per line in
    full-width cells), last_cell_free = window byte +0x45 (default windows set it to 1).
    Returns list of lines, each a list of codes, plus an 'overflow rows' count."""
    lines = [[]]
    u = 0                                   # half-cell units used on the current line
    lim = cells - 1
    for c in codes:
        glyphish = (c & 0x2000) == 0 or c == 0x2020
        if glyphish:
            used = (u + 1) >> 1
            if lim < used or (used == lim and not last_cell_free and (c & 0x4000) == 0):
                lines.append([]); u = 0
            lines[-1].append(c)
            u += 1 if (c == 0x2020 or c & 0x8000) else 2
        elif c == 0x200a:
            lines.append([]); u = 0
    return lines


def render_lines(lines):
    """human readable form of layout() output (ASCII half-width only)"""
    res = []
    for ln in lines:
        s = ''
        for c in ln:
            if c == 0x2020: s += ' '
            elif c & 0x8000: s += chr(c & 0x7f) if (c & 0x7fff) < 0x80 else '?'
            else: s += '■'
        res.append(s)
    return res


def max_ascii_per_line(cells, last_cell_free=True):
    """Largest run of half-width chars that stays on one line (no hanging flags)."""
    n = 0
    u = 0
    lim = cells - 1
    while True:
        used = (u + 1) >> 1
        if lim < used or (used == lim and not last_cell_free):
            return n
        n += 1; u += 1


def fit_check(text, cells, rows, last_cell_free=True, raw=False):
    """text: str with real newlines; returns (n_lines, lines_text, ok)"""
    codes = convert(text.encode('cp932'), raw=raw)
    ls = layout(codes, cells, rows, last_cell_free)
    return len(ls), render_lines(ls), (rows is None or len(ls) <= rows)


def word_wrap(text, cells, last_cell_free=True):
    """Greedy word wrap for English to the half-width capacity of a window; returns str
    with '\\n' inserted (the engine itself NEVER wraps on word boundaries)."""
    cap = max_ascii_per_line(cells, last_cell_free)
    out = []
    for para in text.split('\n'):
        line = ''
        for w in para.split(' '):
            if line and len(line) + 1 + len(w) > cap:
                out.append(line); line = w
            else:
                line = w if not line else line + ' ' + w
        out.append(line)
    return '\n'.join(out)


if __name__ == '__main__':
    for cells in (20, 7, 30, 38):
        print('cells', cells, 'last_cell_free=1 ->', max_ascii_per_line(cells, True),
              'ASCII chars/line, =0 ->', max_ascii_per_line(cells, False))
    t = "Welcome to the club. We hope you enjoy managing this team for many seasons."
    print(word_wrap(t, 20))
    n, ls, ok = fit_check(word_wrap(t, 20), 20, 3)
    print(n, ok); print('\n'.join(ls))
