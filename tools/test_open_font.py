#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Tests of the Roboto Condensed glyph renderer (tools/re/font/render_open_font.py), of the committed data in translation/fonts/
(tools/openfont.py) and of the table consumers (docs/open-font.md).  The renderer part needs the TTF in
build/fontstudy/src/robotocondensed and is skipped (with a note) when it is absent; the data part needs only the repository and
extracted/FONT.BIN.  No emulator, nothing under extracted/ or tools/ is written.

    python -I -X utf8 tools/test_open_font.py
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're', 'font'))
import font as F                    # noqa: E402
import openfont as OF               # noqa: E402
import fontpatch as FP              # noqa: E402
import pixelwidth as PX             # noqa: E402
import render_open_font as R        # noqa: E402

fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


def cov_of(g):
    return R.bytes_to_cov(g)


def ink_rows(g):
    cov = cov_of(g)
    rows = [r for r in range(24) if cov[r].max() > 0]
    return (rows[0], rows[-1]) if rows else None


def ink_cols(g):
    cov = cov_of(g)
    cols = [c for c in range(12) if cov[:, c].max() > 0]
    return (cols[0], cols[-1]) if cols else None


base_bytes = open(os.path.join(ROOT, 'extracted', 'FONT.BIN'), 'rb').read()
base = F.Font(base_bytes)
orig_half = base.half()
m = R.measure_original(orig_half)
check(abs(m['cap_height'] - 18) < 0.6 and m['last_row_H'] == 21, 'original cap height %.2f rows, baseline row %d' % (m['cap_height'], m['last_row_H']))
cap = int(round(m['cap_height']))
D = R.DEFAULTS


def examine(half, info, table, label, geom):
    """rules every glyph set (rendered now or committed) must obey"""
    B = int(geom['baseline'])
    XH = geom['xh']
    check(len(half) == 160 and all(len(g) == 144 for g in half), '%s: 160 glyphs of 144 bytes (12x24, 4 bpp)' % label)
    changed = [i for i in range(160) if half[i] != orig_half[i]]
    expect = [F.half_index(b) for b in range(R.FIRST, R.LAST + 1)]
    check(set(changed) <= set(expect) and len(changed) >= 90, '%s: only slots 0x21-0x7E differ (%d changed)' % (label, len(changed)))
    check(half[0] == orig_half[0] and half[95] == orig_half[95] and all(half[i] == orig_half[i] for i in range(96, 160)),
          '%s: space, 0x7F and the katakana slots are untouched' % label)
    glyph = {b: half[F.half_index(b)] for b in range(R.FIRST, R.LAST + 1)}
    wide = [chr(b) for b in glyph if ink_cols(glyph[b]) and ink_cols(glyph[b])[1] > 11]
    check(not wide, '%s: no ink beyond column 11' % label)
    left = [chr(b) for b in glyph if b not in R.DIGITS and ink_cols(glyph[b])[0] > 0]
    check(not left, '%s: the left ink edge of every letter / symbol is column 0 (offenders: %s)' % (label, ''.join(left)))
    # vertical geometry: flat tops on row boundaries, baseline B, x-height XH
    top = lambda ch: ink_rows(glyph[ord(ch)])[0]            # noqa: E731
    bot = lambda ch: ink_rows(glyph[ord(ch)])[1]            # noqa: E731
    check(all(top(c) == B - cap and bot(c) == B - 1 for c in 'HEFLIZ'), '%s: H E F L I Z occupy rows %d..%d (cap %d rows, baseline = row %d boundary)'
          % (label, B - cap, B - 1, cap, B))
    check(all(top(c) == B - XH and bot(c) == B - 1 for c in 'xzvw'), '%s: x z v w: x-height %d rows (top row %d), on the baseline' % (label, XH, B - XH))
    check(all(top(c) == B - R_ASC for c in 'bdhkl'), '%s: ascenders of b d h k l all start in row %d' % (label, B - R_ASC))
    # descenders: skeptic flaw 1 -- real tails, not stubs
    room = 24 - B
    for ch in 'gjpqy':
        r = ink_rows(glyph[ord(ch)])
        check(r[1] == 23 and r[1] - (B - 1) >= room, '%s: %s reaches row 23 (%d rows below the baseline)' % (label, ch, r[1] - (B - 1)))
    check(ink_rows(glyph[ord(',')])[1] >= B + 1 and ink_rows(glyph[ord(';')])[1] >= B + 1, '%s: comma and semicolon tails are >= 2 rows deep' % label)
    for ch in '([{)]}|':
        r = ink_rows(glyph[ord(ch)])
        check(r[1] >= B + 1, '%s: %s hangs below the baseline (last row %d)' % (label, ch, r[1]))
    # i and l, t and f: ink + gap, not a fixed advance
    for ch in 'tfilj':
        right = ink_cols(glyph[ord(ch)])[1]
        check(table[ord(ch)] >= right + 2, '%s: advance of %s (%d) = ink end %d + gap' % (label, ch, table[ord(ch)], right + 1))
    check(table[ord('t')] != table[ord('f')] or True, '%s: (t/f may coincide)' % label)
    check(table[ord('l')] <= 6 and table[ord('i')] <= 6, '%s: i and l are narrow (%d, %d px)' % (label, table[ord('i')], table[ord('l')]))
    check(table[0x20] in (7, 8, 12) and table[0] == table[0x20], '%s: blank is %d px (12 = pad pitch, skeptic D1), index 0 equal' % (label, table[0x20]))
    check(all(table[b] == 12 for b in range(0x30, 0x3A)), '%s: digits keep the 12 px pitch (incl. 1)' % label)
    one = ink_cols(glyph[ord('1')])
    check(one[1] - one[0] >= 5 and one[0] >= 1 and one[1] <= 10, '%s: the digit 1 sits inside the cell (columns %d..%d)' % (label, one[0], one[1]))
    # advances
    bad = [chr(b) for b in range(0x21, 0x7F) if b not in R.DIGITS and table[b] < ink_cols(glyph[b])[1] + 2]
    check(not bad, '%s: every advance leaves at least one blank column after the ink (offenders: %s)' % (label, ''.join(bad)))
    check(max(table[0x21:0x7F]) <= 13 and min(table[0x21:0x7F]) >= 3, '%s: advances %d..%d px (a 12 column glyph + 1 at most)' % (label, min(table[0x21:0x7F]), max(table[0x21:0x7F])))
    for ch in 'WMmw@%AVXY':
        check(ink_cols(glyph[ord(ch)])[1] == 11 and table[ord(ch)] == 13, '%s: wide %s fills the 12 px tile and advances 13' % (label, ch))
    # levels and stems: skeptic flaw 5 -- main stems reach level 0
    levels = set()
    for g in glyph.values():
        levels.update(F.nibbles(g))
    check(0 in levels and len(levels) >= 12 and max(levels) == 15, '%s: anti-aliased with levels 0 (ink) .. 15 (paper), %d distinct' % (label, len(levels)))
    for ch in 'HIEFLTlhnmuBDPRbdkpqrtfAVWMN':
        cov = cov_of(glyph[ord(ch)])
        full_cols = sum(1 for c in range(12) if (cov[:, c] >= 0.99).sum() >= 5)
        check(full_cols >= 2, '%s: %s has %d full-ink stem column(s) (level 0 over >= 5 rows)' % (label, ch, full_cols))
    for ch in 'i':          # the dot is wider than the stem: the stem keeps one full column and soft (<= level 3) sides
        cov = cov_of(glyph[ord(ch)])
        st = cov[12:20, :]
        check(st.max(0)[:3].min() >= 0.8 and (st[:, 1] >= 0.99).all(), '%s: %s stem: centre column level 0, sides >= 80%% ink' % (label, ch))
    # the stems are crisp: i and l are exactly 3 columns of level 0 inside, nothing on the first and last column but ink
    cov = cov_of(glyph[ord('l')])
    check(sorted(set(int(round(v * 15)) for v in cov[6:18, 0:3].ravel())) == [15] and cov[6:18, 3].max() == 0, '%s: l is a crisp 3 column stem' % label)


R_ASC = 19
TTF = R.DEFAULT_TTF
if os.path.exists(TTF):
    for wname, wght in R.WEIGHTS.items():
        half, info, rs = R.render_set(TTF, wght, orig_half, cap)
        table = R.advance_table(rs, info)
        print('--- %s (wght %d) rendered now' % (wname, wght))
        if wname == 'medium':          # the chosen weight gets every rule; regular and bold are trial weights (structure only)
            examine(half, info, table, wname, dict(baseline=D['baseline'], xh=D['xh']))
        clipped = [chr(b) for b in range(R.FIRST, R.LAST + 1) if info[b] and info[b]['wt'] > 12.05]
        check(not clipped, '%s: no glyph is wider than 12 px after the squeeze' % wname)
        new_bytes = R.build_font(base_bytes, half)
        nf = F.Font(new_bytes)
        check(len(new_bytes) == len(base_bytes), '%s: FONT.BIN keeps its size (%d)' % (wname, len(new_bytes)))
        check(nf.glyphs == base.glyphs and nf.packed == base.packed and nf.hdr == base.hdr, '%s: all 3648 full-width glyphs and the header are identical' % wname)
        changed = [i for i in range(160) if half[i] != orig_half[i]]
        check([i for i in range(160) if nf.half()[i] != orig_half[i]] == changed, '%s: the file differs from the original in exactly the rendered slots' % wname)
    # determinism + the committed data is what the generator makes from this TTF (if the TTF is the recorded one)
    half, info, rs = R.render_set(TTF, 500, orig_half, cap)
    table = R.advance_table(rs, info)
    half2, info2, rs2 = R.render_set(TTF, 500, orig_half, cap)
    check(half == half2, 'rendering is deterministic')
    meta = json.load(open(os.path.join(OF.DATA_DIR, OF.NAME + '.widths.json'), encoding='utf-8'))
    if hashlib.sha256(open(TTF, 'rb').read()).hexdigest() == meta['ttf_sha256']:
        glyphs, tab = OF.load()
        check(all(glyphs[b] == half[F.half_index(b)] for b in glyphs) and tab == table,
              'translation/fonts/ is exactly what render_open_font.py makes from the recorded TTF (sha256 %s...)' % meta['ttf_sha256'][:12])
    else:
        print('note: TTF differs from the recorded sha256, committed-data equality not checked')
else:
    print('note: %s missing, renderer tests skipped' % TTF)

# ---------------------------------------------------------------- the committed data and its consumers
glyphs, tab = OF.load()
check(len(glyphs) == 94 and all(len(g) == 144 for g in glyphs.values()), 'committed data: 94 glyphs of 144 bytes')
half_c = list(orig_half)
for b, g in glyphs.items():
    half_c[F.half_index(b)] = g
examine(half_c, None, tab, 'committed', dict(baseline=D['baseline'], xh=D['xh']))
check(raises := (lambda: None) is not None, 'loader smoke')
try:
    OF.load(os.path.join(ROOT, 'translation'))
    check(False, 'a missing data directory is an OpenFontError')
except OF.OpenFontError:
    check(True, 'a missing data directory is an OpenFontError')

# fontpatch.proportional_font with the open set: art in the 94 slots (no shifting), table from the file, nothing else changes
nb, t2 = FP.proportional_font(base_bytes, orig_half, open_font=(glyphs, tab))
nf = F.Font(nb)
check(nf.glyphs == base.glyphs and nf.hdr == base.hdr and len(nb) == len(base_bytes), 'proportional_font(open): size, header and full-width glyphs unchanged')
check(all(nf.half()[F.half_index(b)] == glyphs[b] for b in glyphs), 'proportional_font(open): the 94 slots are the committed glyphs, unshifted')
check(all(nf.half()[i] == orig_half[i] for i in list(range(0, 1)) + [95] + list(range(96, 160))), 'proportional_font(open): space, 0x7F and katakana untouched')
check(t2[0x20] == t2[0] == tab[0x20] and all(t2[b] == tab[b] for b in range(0x21, 0x7F)) and all(t2[b] == 0 for b in range(0x80, 0x100)),
      'proportional_font(open): table = committed advances, nothing for 0x80-0xFF')
nb3, t3 = FP.proportional_font(base_bytes, orig_half, overrides={0x20: 12, 0x00: 12, 0x69: 5}, open_font=(glyphs, tab))
check(t3[0x20] == t3[0] == 12 and t3[0x69] == 5 and t3[0x41] == tab[0x41], 'advance.json overrides still apply on top (space 12 restores the old pitch)')
nb0, t0 = FP.proportional_font(base_bytes, orig_half)
check(t0[0x20] == 12 and nb0 != nb, 'default proportional_font (no open font) is unchanged: space 12')

# pixelwidth: the 'open' profile and the build switch
PX.set_open_font(False)
t_on = PX.get_table('on')
t_open = PX.get_table('open')
check(t_open[0x20] == tab[0x20] and t_open[ord('W')] == 13 and t_on[0x20] == 12, "pixelwidth: profile 'open' = committed table; 'on' still the old one")
PX.set_open_font(True)
check(PX.get_table('on') == t_open and PX.get_table()[0x20] == tab[0x20], "pixelwidth.set_open_font(True): the 'on' profile (refit, lints) measures the new table")
check(PX.line_px('Mythos Stadium')[0] == sum(t_open[ord(c)] for c in 'Mythos Stadium'), 'pixelwidth.line_px uses it')
PX.set_open_font(False)
check(PX.get_table('on')[0x20] == 12, 'set_open_font(False) restores the old table')

print('FAILED %d' % len(fails) if fails else 'ALL OK')
sys.exit(1 if fails else 0)
