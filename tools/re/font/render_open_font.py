#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Render the 94 ASCII half-width glyphs of FONT.BIN (0x21..0x7E) from the open font Roboto Condensed, with the advance table.
Generator of translation/fonts/robotocondensed_medium_12x24.* (the data the build flag `--open-font on` uses) and trial tool.

    python -I -X utf8 tools/re/font/render_open_font.py [--weights medium] [--out build/fontstudy] [--ttf PATH] [--tag NAME]
        [--baseline 21] [--cap 18] [--xh 14] [--hscale 1.0] [--gamma 1.0] [--comp 0.5] [--tight 0.5] [--space N] [--snap on|off]
        [--export DIR]        write DIR/robotocondensed_<weight>_12x24.bin + .widths.json (the committed build data)

FONT LICENCE (the TTF is NOT part of this repository; only the rendered bitmaps and this generator are).
  Roboto Condensed, Copyright 2011 The Roboto Project Authors (https://github.com/googlefonts/roboto-classic), distributed in
  github.com/google/fonts (ofl/robotocondensed, variable font RobotoCondensed[wght].ttf) under the SIL Open Font License 1.1
  (LICENSES/OFL-1.1.txt).  The rendered bitmaps are a derivative of the font, redistributed under the same licence with the
  copyright notice and licence text (README.md, NOTICE-fonts.md, LICENSES/OFL-1.1.txt).  The font is not sold on its own and the
  bitmaps carry no Reserved Font Name (the metadata lists none).  See docs/open-font.md.

What it does (docs/open-font.md has the method, the numbers and the reasoning):
  * measures the ORIGINAL glyphs (cap height 18 rows, x-height 13.9), sizes Roboto so that its cap height is 18 rows,
  * renders every glyph at 16x supersampling without hinting (Pillow/FreeType, wght axis), then does the grid fitting itself:
      - baseline on a row boundary (default row 21 = 3 rows below it), flat tops of capitals, x-height letters and ascenders on row
        boundaries (x-height 14 rows like the original), round overshoots cut flush, descenders compressed into the rows left
      - the left edge of every glyph on column 0 and its width snapped to whole columns, so vertical stems have crisp edges
        (level 0 = full ink in the stem), digits placed on the tabular 12 px grid (the pen box of the font centred in the cell)
      - glyphs wider than the 12 px tile are squeezed to 12 columns (the tile cannot be wider: docs/open-font.md section 3), the
        squeezed ones get a heavier weight so the strokes keep their thickness
  * maps coverage to the 16 levels (0 = ink, 15 = paper / transparent, gamma 1.0)
  * derives the advance table from the font's own side bearings: advance = ink right edge + right bearing + the mean left bearing of
    the next glyph (the left bearing is removed by the left alignment), minus --tight; space = natural space + mean left bearing
Nothing under tools/ or extracted/ is modified; everything else is written below build/fontstudy/ (or --export).
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import struct
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import font as F        # noqa: E402

DEFAULT_TTF = os.path.join(ROOT, 'build', 'fontstudy', 'src', 'robotocondensed', 'RobotoCondensed[wght].ttf')
WEIGHTS = {'regular': 400, 'medium': 500, 'bold': 700}
SS = 16                       # supersampling factor
CELL_W, CELL_H = 12, 24
FIRST, LAST = 0x21, 0x7E      # glyph slots that are replaced (0x20 stays blank, 0x7F stays as the original)
SUBST = {0x5C: '¥', 0x7E: '¯'}   # the original slot 0x5C is a yen sign and 0x7E an overline: keep those meanings
DIGITS = set(range(0x30, 0x3A))
CANVAS_W, CANVAS_H = 64, 72   # supersampled canvas in px (before * SS)
ORIGIN_X, BASE_Y = 8, 50      # pen origin and baseline inside the canvas (px)
EDGE_T = 0.5                  # coverage of a supersampled pixel that counts as "ink" when measuring extents (edges exact to 1/16 px)
OV = 0.6                      # px: ink within this distance of a landmark is overshoot and is cut / snapped
GAP_MAX = 3                   # blank columns after a glyph never exceed this (the natural gap after . , : ; is 4)
ADV_MAX = 13                  # widest advance: a 12 column glyph + 1 blank column (the original build's widest is 13 too)
ASC_FAMILY = 'bdfhijklt' # lower case letters whose top is above the x-height
DEFAULTS = dict(baseline=21.0, xh=14, hscale=1.0, gamma=1.0, comp=0.5, tight=0.5, space=12, snap=True)   # space 12: the blank code is also the pad of %Nd fields (skeptic D1)


# ------------------------------------------------------------------ measuring the original
def _cov_rows(g):
    n = F.nibbles(g)
    return np.array([[15 - n[r * CELL_W + c] for c in range(CELL_W)] for r in range(CELL_H)], dtype=np.float64) / 15.0


def _stem_edges(cov, col):
    """sub-pixel top and bottom edge (y, rows counted from 0 at the top) of the ink in one column"""
    v = cov[:, col]
    rows = np.where(v > 0)[0]
    return rows[0] + (1 - v[rows[0]]), rows[-1] + v[rows[-1]]


def measure_original(half):
    """Metrics of the original glyph set, from the pixel coverage of 'H' (stem column with most ink), 'z', 'p', 'l'."""
    def g(ch):
        return _cov_rows(half[F.half_index(ord(ch))])
    h = g('H')
    stem = int(np.argmax(h.sum(0)))
    cap_top, base = _stem_edges(h, stem)
    z = g('z')
    xh_top, z_bot = _stem_edges(z, 5)
    p = g('p')
    pcol = int(np.argmax(p[22:, :].sum(0)))
    p_top, p_bot = _stem_edges(p, pcol)
    l_ = g('l')
    l_top, _ = _stem_edges(l_, int(np.argmax(l_.sum(0))))
    return dict(cap_top=cap_top, baseline=base, cap_height=base - cap_top, xh_top=xh_top, xheight=z_bot - xh_top,
                asc_top=l_top, desc_bottom=p_bot, last_row_H=int(np.where(h.max(1) > 0)[0][-1]),
                first_row_H=int(np.where(h.max(1) > 0)[0][0]))


# ------------------------------------------------------------------ rasteriser
class Rasteriser:
    """Renders glyphs of the variable font at one weight into 12x24 coverage arrays (0..1), grid fitted (see the module docstring)."""

    def __init__(self, ttf, wght, cap_rows, baseline=21.0, hscale=1.0, gamma=1.0, xh=14, comp=0.5, tight=0.5, space=None, snap=True):
        self.ttf, self.wght, self.baseline, self.hscale, self.gamma = ttf, wght, float(baseline), hscale, gamma
        self.xh_rows, self.comp, self.tight, self.space_override, self.snap = xh, comp, tight, space, snap
        self._fonts = {}
        probe = self._font(1000.0, wght)
        im = self._draw(probe, 'H', 1200, 1400, 100, 1100)
        rows = np.where(im.max(1) >= 0.5)[0]
        self.cap_ratio = (rows[-1] + 1 - rows[0]) / 1000.0
        self.size = cap_rows / self.cap_ratio            # pixels per em
        self.cap_rows = cap_rows
        self.font = self.font_at(wght)
        # landmarks of this weight, px above the baseline (source = unscaled font at self.size)
        self.cap_nat = self._top('H')
        self.xh_nat = self._top('x')
        self.asc_nat = self._top('l')
        self.XH = int(xh) if xh else int(round(self.xh_nat))
        self.ASC = int(round(self.asc_nat))
        self.slope_asc = (self.ASC - self.XH) / (self.asc_nat - self.xh_nat)
        # stem thickness and its change per wght unit (for the weight compensation of squeezed glyphs)
        w_lo = self._ink_w('l', 400)
        w_hi = self._ink_w('l', 700)
        self.stem_slope = max(1e-3, (w_hi - w_lo) / 300.0)
        self.stem = self._ink_w('l', wght)
        # mean left bearing (px) of the lower case letters: the left bearing is removed by the left alignment, the table puts it back
        lsbs = []
        for ch in 'abcdeghmnopqrsuvwxyz':
            a = self.hires(ch, wght)
            c = np.where(a.max(0) >= EDGE_T)[0]
            lsbs.append((c[0] - ORIGIN_X * SS) / SS)
        self.mean_lsb = float(np.mean(lsbs))
        self.space_adv = self.font.getlength(' ') / SS

    # -- font access
    def _font(self, px, wght):
        f = ImageFont.truetype(self.ttf, px, layout_engine=ImageFont.Layout.BASIC)
        f.set_variation_by_axes([wght])
        return f

    def font_at(self, wght):
        if wght not in self._fonts:
            self._fonts[wght] = self._font(self.size * SS, wght)
        return self._fonts[wght]

    @staticmethod
    def _draw(font, ch, w, h, ox, oy):
        im = Image.new('L', (w, h), 0)
        ImageDraw.Draw(im).text((ox, oy), ch, font=font, fill=255, anchor='ls')
        return np.asarray(im, dtype=np.float32) / 255.0

    def hires(self, ch, wght=None):
        return self._draw(self.font_at(self.wght if wght is None else wght), ch, CANVAS_W * SS, CANVAS_H * SS, ORIGIN_X * SS, BASE_Y * SS)

    def _top(self, ch):
        a = self.hires(ch)
        rows = np.where(a.max(1) >= 0.5)[0]
        return (BASE_Y * SS - rows[0]) / SS

    def _ink_w(self, ch, wght):
        a = self.hires(ch, wght)
        cols = np.where(a.max(0) >= 0.5)[0]
        return (cols[-1] + 1 - cols[0]) / SS

    @staticmethod
    def _area(cum, p0, p1):
        """mean of the piecewise constant data (cumulative sum `cum`, shape n+1 along axis 0) over [p0, p1) for arrays of positions"""
        n = cum.shape[0] - 1

        def at(p):
            p = np.clip(p, 0, n)
            i = np.minimum(np.floor(p).astype(int), n - 1)
            f = (p - i)[:, None]
            return cum[i] * (1 - f) + cum[i + 1] * f
        return (at(p1) - at(p0)) / (p1 - p0)[:, None]

    @staticmethod
    def _bbox(a):
        cols = np.where(a.max(0) >= EDGE_T)[0]
        rows = np.where(a.max(1) >= EDGE_T)[0]
        if len(cols) == 0:
            return None
        return cols[0], cols[-1] + 1, rows[0], rows[-1] + 1

    # -- horizontal plan
    def _hplan(self, w_nat, lsb, adv, centre):
        """-> (offset column, snapped ink width in columns (float), squeezed flag)"""
        s = self.hscale
        off = 0
        if centre:         # the pen box of the (tabular) digit is centred in the 12 px cell
            off = max(0, int(math.floor((CELL_W - adv * s) / 2.0 + lsb * s + 0.5)))
        avail = CELL_W - off
        wt = w_nat * s
        squeezed = False
        if wt > avail:
            wt, squeezed = float(avail), True
        if self.snap:
            wt = min(float(avail), max(1.0, float(math.floor(wt + 0.5))))
        return off, wt, squeezed

    # -- vertical plan
    def _vplan(self, ch, top, bot):
        """-> (landmarks [(target up, source up)] ascending, clip_hi source up or None, clip_flush_bottom, kd, cls)
        up = px above the baseline."""
        depth = max(0.0, -bot)
        desc = depth > OV
        room = CELL_H - self.baseline
        kd = min(1.0, room / depth) if desc else 1.0
        B = self.baseline
        clip_hi = None
        if ch in ASC_FAMILY:
            tt = self.XH + int(math.floor((top - self.xh_nat) * self.slope_asc + 0.5))
            lm = [(self.XH, self.xh_nat), (tt, top)]
            cls = 'asc'
        elif ch.islower():
            lm = [(self.XH, self.xh_nat)]
            clip_hi = self.xh_nat
            cls = 'xh'
        elif abs(top - self.cap_nat) <= OV:
            lm = [(self.cap_rows, self.cap_nat)]
            clip_hi = self.cap_nat
            cls = 'cap'
        elif abs(top - self.xh_nat) <= OV and not desc or (ch in ':;' and abs(top - self.xh_nat) <= OV):
            lm = [(self.XH, self.xh_nat)]
            clip_hi = self.xh_nat
            cls = 'xh'
        else:
            lm = [(min(B, top), top)] if top > 0 else [(1.0, 1.0)]
            cls = 'gen'
        return lm, clip_hi, (not desc), kd, cls

    @staticmethod
    def _inv(up, lm):
        """source up for target up (>= 0): piecewise linear through (0, 0) and the landmarks, extended with the last slope"""
        tg = [0.0] + [p[0] for p in lm]
        sr = [0.0] + [p[1] for p in lm]
        slope = (tg[-1] - tg[-2]) / (sr[-1] - sr[-2]) if sr[-1] != sr[-2] else 1.0
        tg.append(tg[-1] + 1000.0)
        sr.append(sr[-1] + 1000.0 / slope)
        return np.interp(up, tg, sr)

    def render(self, ch, centre=False):
        """-> (coverage 24x12 float array, info dict).  None if the font has no ink for the character."""
        wght = self.wght
        a = self.hires(ch, wght)
        box = self._bbox(a)
        if box is None:
            return None, None
        adv = self.font.getlength(ch) / SS
        lsb0 = (box[0] - ORIGIN_X * SS) / SS
        w0 = (box[1] - box[0]) / SS
        for _ in range(3):                     # weight compensation of squeezed glyphs: the width changes with the weight
            left_hi, right_hi, top_hi, bot_hi = box
            w_nat = (right_hi - left_hi) / SS
            lsb = (left_hi - ORIGIN_X * SS) / SS
            off, wt, squeezed = self._hplan(w_nat, lsb, adv, centre)
            kx = wt / w_nat
            loss = self.stem * (1.0 - kx) / kx
            dw = self.comp * loss / self.stem_slope if (self.comp > 0 and loss > 0) else 0.0
            new = self.wght + min(200.0, dw)
            new = int(round(new / 10.0) * 10)
            if new == wght or dw < 8:
                break
            wght = new
            a = self.hires(ch, wght)
            box = self._bbox(a)
        left_hi, right_hi, top_hi, bot_hi = box
        base_hi = BASE_Y * SS
        top = (base_hi - top_hi) / SS
        bot = (base_hi - bot_hi) / SS
        lm, clip_hi, flush, kd, cls = self._vplan(ch, top, bot)
        if clip_hi is not None:
            a = a.copy()
            a[:max(0, int(round(base_hi - clip_hi * SS))), :] = 0
        if flush:
            a = a.copy()
            a[base_hi:, :] = 0
        # vertical resampling: target row t spans up = B - t .. B - t - 1
        t = np.arange(CELL_H + 1, dtype=np.float64)
        up = self.baseline - t
        src_up = np.where(up >= 0, self._inv(np.maximum(up, 0), lm), up / kd)
        ysrc = base_hi - src_up * SS
        cum_y = np.vstack([np.zeros((1, a.shape[1])), np.cumsum(a, axis=0)])
        rowsv = self._area(cum_y, ysrc[:-1], ysrc[1:])        # 24 x W_hi (mean over the source interval of each target row)
        # horizontal: left ink edge at column `off`, ink width wt columns
        cum_x = np.vstack([np.zeros((1, rowsv.shape[0])), np.cumsum(rowsv.T, axis=0)])   # (W_hi+1) x 24
        c = np.arange(CELL_W + 1, dtype=np.float64)
        xsrc = left_hi + (c - off) * SS / kx
        xs0, xs1 = xsrc[:-1].copy(), xsrc[1:].copy()
        out = np.zeros((CELL_H, CELL_W))
        valid = (xs1 > left_hi) & (xs0 < right_hi)
        if valid.any():
            xs0v = np.maximum(xs0[valid], left_hi)
            xs1v = np.minimum(xs1[valid], right_hi)
            part = self._area(cum_x, xs0v, xs1v)              # n x 24
            frac = (xs1v - xs0v) / (xs1[valid] - xs0[valid])  # a column only partly inside the ink region keeps the ink fraction
            out[:, valid] = (part * frac[:, None]).T
        rsb = adv - lsb0 - w0                                   # right bearing of the glyph at the base weight
        info = dict(ink_w=w0, kx=kx, squeezed=squeezed, kd=kd, bot=-bot, top=top, off=off, wt=wt, wght=wght, cls=cls,
                    lsb=lsb0, adv_nat=adv, rsb=rsb)
        return np.clip(out, 0.0, 1.0), info

    def to_nibbles(self, cov):
        lv = 15 - np.rint(np.power(cov, self.gamma) * 15.0).astype(int)
        return np.clip(lv, 0, 15)


def nib_to_bytes(lv):
    return bytes(((int(lv[r, c]) << 4) | int(lv[r, c + 1])) for r in range(CELL_H) for c in range(0, CELL_W, 2))


def bytes_to_cov(g):
    return _cov_rows(g)


def render_set(ttf, wght, orig_half, cap_rows, baseline=21.0, hscale=1.0, gamma=1.0, xh=14, comp=0.5, tight=0.5, space=12, snap=True):
    """-> (list of 160 half glyph byte strings (originals except the replaced slots), per-char info dict, Rasteriser)"""
    R = Rasteriser(ttf, wght, cap_rows, baseline, hscale, gamma, xh, comp, tight, space, snap)
    half = list(orig_half)
    info = {}
    for b in range(FIRST, LAST + 1):
        ch = SUBST.get(b, chr(b))
        cov, inf = R.render(ch, centre=(b in DIGITS))
        if cov is None:
            info[b] = None             # the font has no glyph: original kept
            continue
        half[F.half_index(b)] = nib_to_bytes(R.to_nibbles(cov))
        info[b] = inf
    return half, info, R


def build_font(base_font_bytes, half_new):
    f = F.Font(base_font_bytes)
    for b in range(FIRST, LAST + 1):
        i = F.half_index(b)
        if half_new[i] != f.half()[i]:
            f.set_half(i, half_new[i])
    return f.build()


# ------------------------------------------------------------------ advance table
def advance_table(R, info):
    """256-byte advance table for the glyph set (index = byte; 0 = "use 12" in the cave; index 0 and 0x20 = the space).
    advance = ink right edge (columns, after the grid fitting) + gap, gap = right bearing of the glyph in the font (scaled with the
    glyph's horizontal factor) + mean left bearing of the lower case letters (the next glyph's left bearing is gone: the glyphs are
    drawn from column 0) - tight, at least 1 blank column.  Digits keep the 12 px tabular pitch of the build, the space is the
    natural space advance + the mean left bearing (or --space)."""
    t = bytearray(256)
    for b in range(FIRST, LAST + 1):
        i = info.get(b)
        if i is None:
            continue
        if b in DIGITS:
            t[b] = 12
            continue
        gap = i['rsb'] * i['kx'] + R.mean_lsb * R.hscale - R.tight
        gap = min(GAP_MAX, max(1, int(math.floor(gap + 0.5))))
        t[b] = min(ADV_MAX, int(round(i['off'] + i['wt'])) + gap)
    sp = R.space_override if R.space_override else int(math.floor(R.space_adv * R.hscale + R.mean_lsb * R.hscale + 0.5))
    t[0x20] = t[0x00] = sp
    return bytes(t)


def table_json(t):
    keys = list(range(0x20, 0x80)) + list(range(0xA0, 0xE0))
    return '{\n' + ',\n'.join('"0x%02X": %d' % (b, t[b]) for b in keys) + '\n}'


def export_data(outdir, name, half_new, table, ttf, wght, params):
    """the committed build data: 94 glyphs of 144 bytes (slots 0x21..0x7E in order) and the advance table with its provenance"""
    os.makedirs(outdir, exist_ok=True)
    glyphs = b''.join(half_new[F.half_index(b)] for b in range(FIRST, LAST + 1))
    base = 'robotocondensed_%s_12x24' % name
    with open(os.path.join(outdir, base + '.bin'), 'wb') as fh:
        fh.write(glyphs)
    meta = {
        'font': 'Roboto Condensed (variable, wght axis)', 'wght': wght,
        'copyright': 'Copyright 2011 The Roboto Project Authors (https://github.com/googlefonts/roboto-classic)',
        'licence': 'OFL-1.1', 'ttf_sha256': hashlib.sha256(open(ttf, 'rb').read()).hexdigest(),
        'generator': 'tools/re/font/render_open_font.py', 'params': params,
        'glyph_file': base + '.bin', 'glyph_sha256': hashlib.sha256(glyphs).hexdigest(),
        'slots': '0x21..0x7E, 94 glyphs x 144 bytes (12x24, 4 bpp, 0 = ink, 15 = paper); 0x5C is a yen sign and 0x7E an overline',
        'advance': {'0x%02X' % b: table[b] for b in range(256) if table[b]},
    }
    with open(os.path.join(outdir, base + '.widths.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(meta, fh, indent=1)
        fh.write('\n')
    return base


# ------------------------------------------------------------------ PNG (RGB) and sheets
def write_png_rgb(path, arr):
    arr = np.ascontiguousarray(np.clip(arr, 0, 255), dtype=np.uint8)
    h, w, _ = arr.shape
    raw = b''.join(b'\0' + arr[y].tobytes() for y in range(h))

    def ch(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                 + ch(b'IDAT', zlib.compress(raw, 9)) + ch(b'IEND', b''))


# backgrounds: (colour, ink colour).  BLUE is an assumed dark blue message window, GREEN an assumed name-tag green (no screenshot of
# the real colours is in the repository): the sheets show how the 16 levels look on dark backgrounds with light ink.
BLUE = (22, 34, 104)
GREEN = (28, 104, 58)
WHITE = (255, 255, 255)
BG = {'blue': (BLUE, WHITE), 'green': (GREEN, WHITE), 'white': (WHITE, (0, 0, 0))}
PANEL_GAP = (90, 90, 90)


def layout(halves, table, s):
    """pen positions of the characters of s: [(x, byte)], total advance in px (proportional rule of the build: table[b], 0 -> 12)"""
    x = 0
    out = []
    for ch in s:
        b = ord(ch)
        adv = table[b] or 12
        out.append((x, b))
        x += adv
    return out, x


def string_cov(halves, table, s):
    pos, total = layout(halves, table, s)
    w = max(total, 1) + CELL_W
    cov = np.zeros((CELL_H, w))
    for x, b in pos:
        i = F.half_index(b)
        if i is None or b == 0x20:
            continue
        g = bytes_to_cov(halves[i])
        cov[:, x:x + CELL_W] = np.maximum(cov[:, x:x + CELL_W], g)
    return cov, total


def paint(cov, bg, fg, scale):
    big = np.kron(cov, np.ones((scale, scale)))[:, :, None]
    return (np.array(bg)[None, None, :] * (1 - big) + np.array(fg)[None, None, :] * big)


def stamp_digits(img, x, y, text, scale, colour):
    for ch in text:
        pat = F._DIG.get(ch, F._DIG[' '])
        for k, bit in enumerate(pat):
            if bit == '1':
                yy, xx = y + (k // 3) * scale, x + (k % 3) * scale
                img[yy:yy + scale, xx:xx + scale] = colour
        x += 4 * scale


def contact_sheet(path, half_orig, half_new, bgs=('blue', 'green')):
    """0x20..0x7E, 4x zoom: per chunk of 32 characters original / new on the dark backgrounds"""
    z = 4
    per = 32
    chunks = [list(range(0x20, 0x20 + per)), list(range(0x40, 0x40 + per)), list(range(0x60, 0x7F))]
    cw = CELL_W * z + 6
    ch_ = CELL_H * z + 6
    width = 10 + per * cw
    blocks = []
    for chunk in chunks:
        for bgname in bgs:
            bg, fg = BG[bgname]
            for which, hs in (('orig', half_orig), ('new', half_new)):
                row = np.zeros((ch_, width, 3)) + np.array(bg)
                for k, b in enumerate(chunk):
                    cov = bytes_to_cov(hs[F.half_index(b)])
                    row[3:3 + CELL_H * z, 5 + k * cw:5 + k * cw + CELL_W * z] = paint(cov, bg, fg, z)
                    row[:, 5 + k * cw + CELL_W * z + 2:5 + k * cw + CELL_W * z + 3] = np.array(bg) * 0.85 + np.array(fg) * 0.15
                blocks.append(row)
            blocks.append(np.zeros((6, width, 3)) + np.array(PANEL_GAP))
        blocks.append(np.zeros((10, width, 3)) + np.array((200, 60, 60)))
    write_png_rgb(path, np.vstack(blocks))


SAMPLES = ['Mythos Stadium', 'Cloudy', '15:00 KICK OFF', 'OPTIONS', 'Player Names', 'Commentary Text', 'Camera Type',
           'Near/Mid/Far', "Set this month's advertising budget.", 'Kasamatsu  Hisanaga  Kanawaki  Narusawa',
           'Change the line-up. Select who to substitute, then who comes on.', 'Mark Keiji Kijima 23 yrs 3200 man']
# strings that show the flaws the skeptic found (descenders, punctuation, word space, t f 1 i l, wide capitals, digits)
STRESS = ['gypsy jumping quickly, my dog (2) [A] {b} | #5', 'Wilfred Wolf-Williams: "Illegal fifty-five little lilies."',
          'WMmw@%AVXY WAVE MAXIM Wow! Mum swims', '1 11 101 1,250,000,000 14:30 Age 25 No.1 123456 0.75',
          'The quick brown fox jumps over the lazy dog.', 'Ito, Yuji; Sato, Kenji (c) - 90 min.', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
          'abcdefghijklmnopqrstuvwxyz 0123456789', '!?&$+=-/<>*^_`~\\', 'ffi fl ft tt rt it ij if of off tf']
BUDGET = 468        # 39 half-width cells, docs/font-widths.md section 5


def strip_sheet(path, strings, halves_new, table_new, halves_orig=None, table_orig=None, scale=1, bgs=('blue', 'green'), budget=True):
    """one block per string and background: [orig], new at `scale`x; the red line marks 468 px (39 cells); the digits are the width"""
    z = scale
    rows = []
    wmax = 0
    cache = []
    for s in strings:
        cn, tn = string_cov(halves_new, table_new, s)
        co, to = string_cov(halves_orig, table_orig, s) if halves_orig else (None, 0)
        cache.append((s, cn, tn, co, to))
        wmax = max(wmax, cn.shape[1], (co.shape[1] if co is not None else 0), BUDGET + CELL_W if budget else 0)
    width = (wmax + 50) * z
    for s, cn, tn, co, to in cache:
        for bgname in bgs:
            bg, fg = BG[bgname]
            for cov, tot in ((co, to), (cn, tn)):
                if cov is None:
                    continue
                img = np.zeros((CELL_H * z + 4, width, 3)) + np.array(bg)
                p = paint(cov, bg, fg, z)
                img[2:2 + CELL_H * z, 4:4 + p.shape[1]] = p
                if budget:
                    mark = BUDGET * z + 4
                    img[:, mark:mark + 1] = (230, 40, 40)
                stamp_digits(img, width - 44 * z // 2 if z <= 2 else width - 44, 8, '%d' % tot, max(1, min(z, 2)), fg)
                rows.append(img)
        rows.append(np.zeros((6, width, 3)) + np.array((200, 60, 60)))
    write_png_rgb(path, np.vstack(rows))
    return [(s, to, tn) for s, cn, tn, co, to in cache]


# ------------------------------------------------------------------ strings of the database
ESC = re.compile(r'@[A-Za-z0-9]{0,2}/|=[A-Za-z0-9]{1,2}/|@')


def db_lines(tdir=None):
    """display lines (en split at \\n, escape codes removed) of the fmt-free records of translation/*.jsonl (not translation/refit)"""
    tdir = tdir or os.path.join(ROOT, 'translation')
    out = []
    for fn in sorted(glob.glob(os.path.join(tdir, '*.jsonl'))):
        with open(fn, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                en = r.get('en')
                if not en or r.get('fmt'):
                    continue
                if any(c in en for c in '%#$'):
                    continue
                for ln in re.split(r'\n|<br>', ESC.sub('', en)):
                    if ln.strip():
                        out.append((r['id'], ln))
    return out


def width_of(table, s):
    return sum((table[ord(c)] or 12) if 0x20 <= ord(c) < 0x80 else 24 for c in s)


# ------------------------------------------------------------------ main
def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--weights', default='medium')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'fontstudy'))
    ap.add_argument('--ttf', default=DEFAULT_TTF)
    ap.add_argument('--hscale', type=float, default=DEFAULTS['hscale'], help='global horizontal scale before the per-glyph squeeze (default 1.0)')
    ap.add_argument('--baseline', type=float, default=DEFAULTS['baseline'], help='baseline as a row boundary (21 = 3 rows below it; the original is at 21.5)')
    ap.add_argument('--cap', type=int, default=None, help='cap height in rows (default: measured from the original, rounded)')
    ap.add_argument('--xh', type=int, default=DEFAULTS['xh'], help='x-height in rows (0 = natural, rounded; default 14 like the original 13.9)')
    ap.add_argument('--gamma', type=float, default=DEFAULTS['gamma'], help='< 1 darkens the anti-aliasing fringe')
    ap.add_argument('--comp', type=float, default=DEFAULTS['comp'], help='fraction of the stem thickness lost by a squeeze that is given back with a heavier weight')
    ap.add_argument('--tight', type=float, default=DEFAULTS['tight'], help='px taken from every letter gap')
    ap.add_argument('--space', type=int, default=None, help='force the space advance (default: derived)')
    ap.add_argument('--snap', choices=['on', 'off'], default='on', help='snap glyph widths to whole columns')
    ap.add_argument('--tag', default='', help='suffix for the output file names, e.g. _h90')
    ap.add_argument('--export', default=None, help='write the committed build data (glyph .bin + .widths.json) to this directory')
    ap.add_argument('--no-db', action='store_true', help='skip the database line statistics')
    a = ap.parse_args(argv)
    base = F.Font.load()
    base_bytes = open(os.path.join(ROOT, 'extracted', 'FONT.BIN'), 'rb').read()
    orig_half = base.half()
    m = measure_original(orig_half)
    cap_rows = a.cap or int(round(m['cap_height']))
    print('original metrics (rows from the top, sub-pixel): ' + ', '.join('%s=%.2f' % kv for kv in m.items()))
    print('cap height used: %d rows, baseline boundary y=%.1f, hscale %.2f' % (cap_rows, a.baseline, a.hscale))
    import fontpatch as FP
    orig_cur, table_orig = FP.proportional_font(base_bytes, orig_half)
    lines = [] if a.no_db else db_lines()
    params = dict(baseline=a.baseline, cap=cap_rows, xh=a.xh, hscale=a.hscale, gamma=a.gamma, comp=a.comp, tight=a.tight,
                  space=a.space, snap=a.snap == 'on')
    for wname in a.weights.split(','):
        wght = WEIGHTS[wname]
        half_new, info, R = render_set(a.ttf, wght, orig_half, cap_rows, a.baseline, a.hscale, a.gamma, a.xh, a.comp, a.tight, a.space, a.snap == 'on')
        table = advance_table(R, info)
        name = wname + a.tag
        os.makedirs(a.out, exist_ok=True)
        new_bytes = build_font(base_bytes, half_new)
        with open(os.path.join(a.out, 'FONT_rc_%s.BIN' % name), 'wb') as fh:
            fh.write(new_bytes)
        with open(os.path.join(a.out, 'widths_rc_%s.json' % name), 'w') as fh:
            fh.write(table_json(table))
        orig_half_cur = F.Font(orig_cur).half()
        sheet_path = os.path.join(a.out, 'sheet_%s.png' % name)
        contact_sheet(sheet_path, orig_half_cur, half_new)
        paths = []
        for z in (1, 2, 4):
            p = os.path.join(a.out, 'strips%dx_%s.png' % (z, name))
            strs = SAMPLES + STRESS if z == 1 else (SAMPLES[:7] + STRESS[:4] if z == 2 else SAMPLES[:3] + [SAMPLES[4], STRESS[2], STRESS[3]])
            strip_sheet(p, strs, half_new, table, orig_half_cur, table_orig, scale=z, budget=(z == 1))
            paths.append(p)
        totals = [(s, width_of(table_orig, s), width_of(table, s)) for s in SAMPLES]
        print('=== %s (wght %d): size %.2f px/em, cap ratio %.4f, x-height %d rows (natural %.2f), ascender %d (%.2f), stem %.2f px, mean lsb %.2f, space adv %.2f'
              % (name, wght, R.size, R.cap_ratio, R.XH, R.xh_nat, R.ASC, R.asc_nat, R.stem, R.mean_lsb, R.space_adv))
        sq = ['%s(%.1f->%.0f w%d)' % (chr(b), i['ink_w'] * a.hscale, i['wt'], i['wght']) for b, i in info.items() if i and i['squeezed']]
        print('squeezed horizontally (ink wider than the available columns): %d glyphs: %s' % (len(sq), ' '.join(sq)))
        dsq = ['%s(k=%.2f %.1fpx)' % (chr(b), i['kd'], i['bot']) for b, i in info.items() if i and i['kd'] < 0.999]
        print('descender compressed to fit the %.0f rows below the baseline: %d glyphs: %s' % (CELL_H - a.baseline, len(dsq), ' '.join(dsq)))
        print('space advance %d px; advances: ' % table[0x20] + ' '.join('%s%d' % (chr(b), table[b]) for b in range(0x21, 0x7F)))
        print('written', os.path.join(a.out, 'FONT_rc_%s.BIN' % name), len(new_bytes), 'bytes (orig %d)' % len(base_bytes))
        print('sheets', sheet_path, ' '.join(paths))
        mean_o = sum(table_orig[b] for b in range(0x21, 0x7F)) / 94
        mean_n = sum(table[b] for b in range(0x21, 0x7F)) / 94
        print('mean advance 0x21-0x7E: original(build) %.2f, new %.2f px' % (mean_o, mean_n))
        print('sample strings, total advance px: orig(build) -> new')
        for s, to, tn in totals:
            print('  %-66s %4d -> %4d' % (repr(s), to, tn))
        if lines:
            wo = sorted(((width_of(table_orig, ln), len(ln), i, ln) for i, ln in lines), reverse=True)
            wn = {(i, ln): width_of(table, ln) for i, ln in lines}
            over_o = sum(1 for x in wo if x[0] > BUDGET)
            over_n = sum(1 for k, v in wn.items() if v > BUDGET)
            print('database lines wider than %d px (39 cells): orig %d, new %d  (of %d)' % (BUDGET, over_o, over_n, len(lines)))
            tot_o = sum(x[0] for x in wo)
            tot_n = sum(wn.values())
            print('sum of line widths: orig %d, new %d px (%.1f%%)' % (tot_o, tot_n, 100.0 * tot_n / tot_o))
        if a.export:
            b = export_data(a.export, wname, half_new, table, a.ttf, wght, params)
            print('exported', os.path.join(a.export, b + '.bin'), 'and .widths.json')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
