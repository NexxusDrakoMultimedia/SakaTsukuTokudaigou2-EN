"""pixelwidth: pixel-width model of the proportional half-width font (docs/pixel-widths.md).

Shared by tools/transcheck.py, tools/transwork.py and tools/winwidth.py (`--width-mode cells|pixels`).  Pure functions, no
disc access except reading extracted/FONT.BIN once to derive the advance table.

    python -I -X utf8 tools/pixelwidth.py table              the advance table of the profile, grouped by advance
    python -I -X utf8 tools/pixelwidth.py width "TEXT"       pixel width, pen start of the last glyph, fit per window
    python -I -X utf8 tools/pixelwidth.py wrap  "TEXT" 33    word wrap at a limit (cells; --width-mode pixels for the px rule)

THE ENGINE RULE (docs/font-widths.md s5, docs/proportional-font.md s4.3; the cave hook H2 of tools/fontpatch.py):
a glyph is drawn when its pen START satisfies  pen - x0 <= A*(W-1),  A = 24, W = window cells (17 bubble, 20 message window).
In half cells: max_cells = 2W-1 (33 / 39), so the limit for the START of a glyph is 12*(max_cells-1) px (384 / 456) and the
nominal pen travel is 12*max_cells px (396 / 468).  A line therefore fits iff

        sum(advance of all glyphs but the last) <= 12*(max_cells - 1)          ("start of the last glyph")

which for the monospaced font (every advance 12) is exactly `cells <= max_cells`.  A last glyph may reach 13 px: its pen end can
be 1 px above 12*max_cells (the 12 px reserve of the "last cell free" flag absorbs it).  The game has no word wrap: a line
that does not fit breaks in the middle of a word and the rest starts a new row (`wrap_rows`).

PROFILES (advance tables), selected with `--px-profile`:
    on     the table the build writes with `--proportional-font on`: tools/fontpatch.proportional_font() on extracted/FONT.BIN
           (+ translation/font/advance.json overrides, as tools/build_patch.apply_prop_font).  ASCII 5..13 px, digits 12, SPACE 12
           (skeptic D1: padded numeric fields keep their pitch), everything without a rule 12.  Default.
    ideal  the measured hybrid-H table of docs/font-widths.md (tools/re/font/widths_meta.json): the same but SPACE 6 px.  Shows what
           a narrow space would buy; not what the build does.
    open   the table of `--open-font on` (tools/openfont.py, Roboto Condensed Medium, space 7 px); the 'on' profile becomes this one while
           a build with --open-font on runs (set_open_font), so refit and the lints measure what is built.
    off    every glyph 12 px: reproduces the cell rule exactly (used by the tests as an identity check).

DYNAMIC TOKENS (names, numbers, #tokens) have unknown widths; the validator charges a WORST CASE, never the average:
    text tokens   #sname# #tkNN# (10 cells), other #xxx# (8), %s (8 or the explicit field width), $N (6):  n glyphs x 13 px
                  (13 = the widest advance in the table: a name made only of W / M / A ... cannot be wider)
    numeric       %d (3) %D (6) %m (15, jp money style: '13 Oku 1500 Man') %f (6) %x %X (4), or the explicit field width of %5d ...:  n glyphs x 12 px
                  (digits are fixed 12 px in the table; the sign, the thousands comma and spaces are <= 12)
    %%            one '%' glyph; colour / window tokens (@Y/ @ =K/ =) and raw <XX>: 0 px (as in cells_of_line)
The cell counts n are those of translib.WIDTH_SUBST / _fmt_cells (docs/capacity-ratio.md s7), so a line that carries a name token
is charged 130 px for it, i.e. more than the 120 px of the cell rule: pixel mode is NOT strictly more lenient than cell mode for
such lines, and capital-heavy text (13 px glyphs) can be wider than its cell count.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T  # noqa: E402

CELL_PX = 12          # one half cell = 12 px of pen travel in the original font
WIDE_PX = 13          # widest advance of the proportional table (30 wide letters): worst case for one glyph of a text token
FULL_PX = 24          # a full-width glyph
PROFILES = ('on', 'ideal', 'off', 'open')
DEFAULT_PROFILE = 'on'
META_PATH = os.path.join(HERE, 're', 'font', 'widths_meta.json')
FONT_PATH = os.path.join(T.ROOT, 'extracted', 'FONT.BIN')
ADV_OVERRIDES = os.path.join(T.ROOT, 'translation', 'font', 'advance.json')

_TABLES = {}
_OPEN_SWITCH = False       # build_patch --open-font on: the 'on' profile (the table of the build) is the open font table


def set_open_font(flag):
    """Make the 'on' profile (the table of the build) the Roboto Condensed table of tools/openfont.py (build_patch --open-font on), so refit
    and the lints measure the glyph set that is built.  Clears the cached tables."""
    global _OPEN_SWITCH
    flag = bool(flag)
    if flag != _OPEN_SWITCH:
        _OPEN_SWITCH = flag
        _TABLES.clear()


def _open_table():
    """tools/openfont.py advance table (space 7, digits 12) + translation/font/advance.json overrides, as the build applies them."""
    import fontpatch as FPT
    import openfont
    t = list(openfont.table())
    if os.path.exists(ADV_OVERRIDES):
        with open(ADV_OVERRIDES, encoding='utf-8') as fh:
            for b, px in FPT.parse_overrides(json.load(fh)).items():
                t[b] = px
    return t


def _meta_table():
    """256 entries from widths_meta.json (hybrid H, space 6), digits forced to 12 like fontpatch; 0 = use 12."""
    with open(META_PATH, encoding='utf-8') as fh:
        meta = json.load(fh)
    t = [0] * 256
    for k, g in meta['glyphs'].items():
        b = int(k, 16)
        if b < 256 and 0x21 <= b <= 0x7E:
            t[b] = g['advance']
    t[0x20] = 6
    for b in range(0x30, 0x3A):
        t[b] = 12
    return t


def _on_table():
    """The table of `build_patch.py --proportional-font on` (fontpatch.proportional_font + advance.json overrides)."""
    import fontpatch as FPT
    if os.path.exists(FONT_PATH):
        with open(FONT_PATH, 'rb') as fh:
            _font, table = FPT.proportional_font(fh.read())
        t = list(table)
    else:                                         # no extracted/ (a fresh clone): the measured table with the build's space / digits
        t = _meta_table()
        t[0x20] = FPT.SPACE_ADV
    if os.path.exists(ADV_OVERRIDES):
        with open(ADV_OVERRIDES, encoding='utf-8') as fh:
            for b, px in FPT.parse_overrides(json.load(fh)).items():
                t[b] = px
    return t


def get_table(profile=DEFAULT_PROFILE):
    """-> list of 256 advances in px for the codes 0x00..0xFF (a stored 0 means 12 px, as in the cave); cached per profile."""
    if profile not in PROFILES:
        raise ValueError('px profile must be one of %s, not %r' % (', '.join(PROFILES), profile))
    if profile not in _TABLES:
        if profile == 'off':
            t = [CELL_PX] * 256
        elif profile == 'ideal':
            t = _meta_table()
        elif profile == 'open' or _OPEN_SWITCH:
            t = _open_table()
        else:
            t = _on_table()
        _TABLES[profile] = [x or CELL_PX for x in t]
    return _TABLES[profile]


def glyph_px(ch, table):
    o = ord(ch)
    if o < 0x100:
        return table[o]
    if 0xff61 <= o <= 0xff9f:
        return CELL_PX
    return FULL_PX


_NUMERIC = frozenset('dDmMfxX')


def _token_advances(tok, table):
    """Worst-case advances of one control token (see the module docstring), [] for a zero-width token."""
    c = tok[0]
    wide = max(table[0x21:0x7F])          # widest advance of the profile (13 for on / ideal, 12 for off: the identity profile)
    if c == '%':
        if tok == '%%':
            return [table[ord('%')]]
        n = T._fmt_cells(tok)
        km = re.match(r'%-?[0-9]*(?:\.[0-9]+)?([sdDmMfxX])', tok)
        if not km:                                # malformed field such as '%.d': 0 cells, like translib._fmt_cells
            return []
        kind = km.group(1)
        return [CELL_PX if kind in _NUMERIC else wide] * n
    if c in '@=' or c == '<':
        return []
    for rx, w in T.WIDTH_SUBST:
        if rx.fullmatch(tok):
            return [wide] * w
    return []


def advances(line, table=None, mode='game'):
    """Pen advances (px) of every glyph of one line (no newline), dynamic tokens at their worst case.  Browser text has no
    pixel rule here (its limit is None); mode 'browser' counts the printf fields only."""
    table = table or get_table()
    out = []
    pos = 0
    rx = T.token_re(mode)
    for m in rx.finditer(line):
        out.extend(glyph_px(c, table) for c in line[pos:m.start()])
        tok = m.group(0)
        if mode == 'browser':
            out.extend(_token_advances(tok, table) if tok[0] == '%' else [])
        else:
            out.extend(_token_advances(tok, table))
        pos = m.end()
    out.extend(glyph_px(c, table) for c in line[pos:])
    return out


def line_px(line, table=None, mode='game'):
    """-> (pen end px, pen start of the last glyph px) of one line; (0, 0) for an empty line."""
    adv = advances(line, table, mode)
    if not adv:
        return 0, 0
    end = sum(adv)
    return end, end - adv[-1]


def limit_px(max_cells):
    """nominal pen travel of a window: 12 * max_cells (396 bubble, 468 message window)."""
    return CELL_PX * max_cells


def start_limit_px(max_cells):
    """the engine's limit for the START of a glyph: 12 * (max_cells - 1) = A*(W-1) (384 / 456)."""
    return CELL_PX * (max_cells - 1)


def fits(adv, max_cells):
    """True when the glyph advances `adv` (one line) are all drawn on one row of a window of `max_cells` half cells."""
    return not adv or sum(adv) - adv[-1] <= start_limit_px(max_cells)


def over_px(adv, max_cells):
    """px by which the last glyph starts beyond the engine limit (0 when the line fits)."""
    return max(0, (sum(adv) - adv[-1] if adv else 0) - start_limit_px(max_cells))


def wrap_rows(adv, max_cells):
    """Rows one line occupies when the engine breaks it at the glyph that no longer starts inside the window (no word wrap)."""
    rows, pen = 1, 0
    lim = start_limit_px(max_cells)
    for a in adv:
        if pen > lim:
            rows += 1
            pen = 0
        pen += a
    return rows


def check_line(line, max_cells, table=None, mode='game', wclass=None):
    """-> dict(ok, px (pen end), start (pen start of the last glyph), limit (nominal px), over (px), rows).
    For a fixed-column CELL string (wclass 'CELL': its window is not known to use the proportional hook, docs/window-widths.md s3.2)
    the cell rule must hold as well, so that the pixel rule never admits a line the monospaced rule refused."""
    adv = advances(line, table, mode)
    end = sum(adv)
    start = end - adv[-1] if adv else 0
    over = over_px(adv, max_cells)
    ok = over == 0
    rows = wrap_rows(adv, max_cells)
    if wclass == 'CELL' and T.cells_of_line(line, mode) > max_cells:
        ok = False
        over = max(over, CELL_PX)
        rows = max(rows, -(-T.cells_of_line(line, mode) // max_cells))
    return {'ok': ok, 'px': end, 'start': start, 'limit': limit_px(max_cells), 'over': over, 'rows': rows}


# ----------------------------------------------------------------------------------------------- word wrap

def _width_ok(line, max_cells, width_mode, table, mode):
    if width_mode == 'pixels':
        return fits(advances(line, table, mode), max_cells)
    return T.cells_of_line(line, mode) <= max_cells


def wrap_text(text, max_cells, width_mode='cells', table=None, mode='game'):
    """Greedy word wrap of `text` (existing newlines are kept as paragraph breaks) so that every line fits `max_cells`
    (cells or pixels by `width_mode`).  A single word wider than the window is put on a line of its own (the caller sees the
    overflow with check_line).  Spaces are the only break points; the space at a break is dropped."""
    out = []
    for para in text.split('\n'):
        words = para.split(' ')
        cur = ''
        started = False
        for w in words:
            if not started:
                cur, started = w, True
                continue
            cand = cur + ' ' + w
            if _width_ok(cand, max_cells, width_mode, table, mode):
                cur = cand
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return '\n'.join(out)


# ------------------------------------------------------------------------------------------------- CLI

def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['table', 'width', 'wrap'])
    ap.add_argument('text', nargs='?', default='')
    ap.add_argument('cells', nargs='?', type=int, default=33)
    ap.add_argument('--px-profile', choices=PROFILES, default=DEFAULT_PROFILE)
    ap.add_argument('--width-mode', choices=['cells', 'pixels'], default='cells')
    a = ap.parse_args(argv)
    t = get_table(a.px_profile)
    text = a.text.replace('\\n', '\n')
    if a.cmd == 'table':
        by = {}
        for b in range(0x20, 0x7F):
            by.setdefault(t[b], []).append(chr(b))
        for px in sorted(by):
            print('%2d px  %s' % (px, ''.join(by[px])))
    elif a.cmd == 'width':
        for l in text.split('\n'):
            r = check_line(l, 33, t)
            r2 = check_line(l, 39, t)
            print('%3d px  last glyph starts at %3d  cells %2d  bubble(33) %s  message(39) %s  | %s' % (
                r['px'], r['start'], T.cells_of_line(l), 'ok' if r['ok'] else 'OVER %d px' % r['over'],
                'ok' if r2['ok'] else 'OVER %d px' % r2['over'], l))
    else:
        print(wrap_text(text, a.cells, a.width_mode, t))
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
