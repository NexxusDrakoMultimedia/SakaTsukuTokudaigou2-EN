#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Tests of --small-prop (tools/fontpatch.py SMALL_SRC, docs/layout-issues.md section 17): the 16 px windows of OPTION.BIN (option / sound-test lists) and
TRAINING.BIN (Practice player-info panel) get the proportional advance (table scaled by 2/3) instead of the fixed 8 px of the font cave's `A != 24` path.
Nothing starts an emulator.

    python -I -X utf8 tools/test_smallprop.py

* the lookup table, the routine's size / literals / registered reserve, every word against capstone;
* `sm_adv` executed in tools/sh4sim.py for every code 0..255 and every window advance -128..127, both advance tables (default proportional and
  Roboto Condensed Medium): A == 16 gives (t * 16 + 12) / 24 (t = 0 -> 12), every other A gives exactly what the unchanged font cave gives; PR, r4, r14, r15,
  MACL and memory are untouched;
* isolation on the real files: the hook literal of OPTION and TRAINING is the only byte difference of those overlays against a small-prop-off build, every
  other overlay (EVENT, SCDRF, SEARCH, GAME, NEWS, ...) is byte-identical, 1ST_READ.BIN differs only inside the unused tail of the font cave reserve
  (the default cave bytes, the table, the money / lin / align caves are identical); default (flag off) bytes are those of a build without the option;
* the REAL tsString layout function of the REAL patched TRAINING / OPTION overlays at A = 16: pen positions of 'Hiroshi Hase', 'Training', 'Advance Schedule',
  'BGM' are the scaled advances; blanks, digits and the A = 24 control are unchanged; the 'Event' path (EVENT.BIN) is not hooked differently;
* refused: gap1 placement, variants ABC, no glyph table, snap + small on one overlay.
"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontcheck as FC        # noqa: E402
import fontpatch as FP        # noqa: E402
import moneypatch             # noqa: E402,F401  (registers the money claims)
import openfont as OF         # noqa: E402
import patchengine as PE      # noqa: E402
import sh4sim                 # noqa: E402
import test_alignfix as TA    # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

HAVE = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'))
CT = FP.placement()
CAVE, TABLE = CT
SM = FP.small_entry(CT)
WIN, RET = 0x00100000, 0x00002000
SMALL = list(FP.SMALL_FILES)
IMG = FP.IMG_BASE

_cache = {}


def tables():
    if 'tables' not in _cache:
        out = {}
        for name, of in (('default', None), ('open', OF.load())):
            o, rep = FP.make_patches(FP.read_extracted, paths=[], open_font=of)
            out[name] = bytes(rep['table'])
        _cache['tables'] = out
    return _cache['tables']


def machine(table, small=True, scale=False):
    m = sh4sim.Machine()
    m.load(CAVE, FP.cave_bytes(CT, scale=scale, small=small))
    m.load(TABLE, table)
    return m


def adv(m, entry, code, a):
    m.mem[WIN + 62] = a & 0xFF
    m.R[14], m.R[4], m.PR = WIN, code, RET
    m.run(entry, RET)
    return m.R[0] & 0xFFFFFFFF


def want16(table, code):
    t = table[code & 0xFF] or 12
    return (t * 16 + 12) // 24


class Routine(unittest.TestCase):
    def test_lookup_table_is_the_scaled_advance(self):
        self.assertEqual(len(FP.SMALL_TAB), 25)
        for t in range(1, 25):
            self.assertEqual(FP.SMALL_TAB[t], (t * 16 + 12) // 24, t)
        self.assertEqual(FP.SMALL_TAB[12], 8)                # digits / blanks / unlisted codes keep the original 8 px
        self.assertEqual(FP.SMALL_TAB[24], 16)               # a 24 px advance fills the 16 px cell
        # the identity with the A >> 1 rule of the unpatched cave for t = 12
        self.assertEqual((12 * 16 + 12) // 24, (16 + 1) >> 1)

    def test_layout_fits_the_reserve(self):
        code = FP.small_bytes(CT)
        self.assertEqual(len(code) % 4, 0)
        self.assertLessEqual(FP.SMALL_OFF + len(code), FP.RESERVE)
        self.assertGreaterEqual(FP.SMALL_OFF, FP.CAVE_SIZE_SCALE)           # behind the --prop-scale cave too
        self.assertEqual(FP.SMALL_OFF % 4, 0)
        self.assertEqual(code[FP.SMALL_TAB_OFF:FP.SMALL_TAB_OFF + 25], FP.SMALL_TAB)
        lits = struct.unpack_from('<II', code, 32)
        self.assertEqual(lits, (TABLE, CAVE + FP.SMALL_OFF + FP.SMALL_TAB_OFF))
        full = FP.cave_bytes(CT, small=True)
        self.assertEqual(len(full), FP.SMALL_OFF + len(code))
        self.assertEqual(full[:FP.CAVE_SIZE], FP.cave_bytes(CT))             # default cave bytes untouched
        self.assertFalse(any(full[FP.CAVE_SIZE:FP.SMALL_OFF]))
        both = FP.cave_bytes(CT, scale=True, small=True)
        self.assertEqual(both[:FP.CAVE_SIZE_SCALE], FP.cave_bytes(CT, scale=True))
        self.assertEqual(both[FP.SMALL_OFF:], full[FP.SMALL_OFF:])
        self.assertEqual(FP.cave_bytes(CT, small=False), FP.cave_bytes(CT))  # off = the old bytes

    @unittest.skipIf(MD is None, 'capstone missing')
    def test_every_word_decodes(self):
        code = FP.small_bytes(CT)
        names = []
        for i in range(0, FP.SMALL_TAB_OFF - 8, 2):
            ins = list(MD.disasm(code[i:i + 2], CAVE + FP.SMALL_OFF + i))
            self.assertTrue(ins, 'undecodable word at +%#x' % i)
            names.append(('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip())
        self.assertEqual(names[0].replace(' ', ''), 'mov#62,r0')
        self.assertIn('cmp/eq r3,r2', [n.replace(', ', ',') for n in names])
        self.assertTrue(any(n.startswith('bf ') and int(n.split()[1], 16) == CAVE for n in names), names)     # the tail jump to the unchanged entry
        self.assertIn('rts', names)
        self.assertFalse(any('mul' in n or 'macl' in n for n in names), 'no multiply / MACL')

    def test_claim_stays_inside_the_font_cave_reserve(self):
        self.assertEqual(PE.REGISTRY.addr('font.cave'), CAVE)
        self.assertEqual(PE.REGISTRY.size('font.cave'), FP.RESERVE)
        self.assertEqual(FP.small_entry(CT), CAVE + FP.SMALL_OFF)
        self.assertLess(FP.SMALL_OFF + len(FP.small_bytes(CT)), FP.RESERVE + 1)


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Executed(unittest.TestCase):
    def test_all_codes_all_window_advances(self):
        for name, tab in tables().items():
            ms = machine(tab, small=True)
            mc = machine(tab, small=False)
            for a in range(-128, 128):
                for code in range(256):
                    r = adv(ms, SM, code, a)
                    if a == 16:
                        self.assertEqual(r, want16(tab, code), (name, a, code))
                    else:
                        self.assertEqual(r, adv(mc, CAVE, code, a), (name, a, code))

    def test_registers_and_memory_untouched(self):
        for name, tab in tables().items():
            for a in (16, 24, 32, 10, 1):
                m = machine(tab)
                m.mem[WIN + 62] = a
                m.R[14], m.R[4], m.PR = WIN, 0x8000 | 0x69, RET
                m.R[15] = 0x00300000
                before_mem = dict(m.mem)
                keep = {i: 0x11110000 + i for i in (5, 6, 7, 8, 9, 10, 11, 12, 13)}
                for i, v in keep.items():
                    m.R[i] = v
                m.run(SM, RET)
                self.assertEqual(m.PR, RET)
                self.assertEqual(m.R[4], 0x8000 | 0x69)
                self.assertEqual(m.R[14], WIN)
                self.assertEqual(m.R[15], 0x00300000)
                for i, v in keep.items():
                    self.assertEqual(m.R[i], v, (a, i))
                self.assertEqual(m.mem, before_mem)

    def test_narrow_letters_shrink_and_nothing_else(self):
        tab = tables()['open']
        i, l, t, W, sp, d5 = (want16(tab, ord(c)) for c in 'ilTW 5')
        self.assertLess(i, 8)
        self.assertLess(l, 8)
        self.assertEqual(want16(tab, 0), 8)                   # the blank
        self.assertEqual(want16(tab, ord('5')), 8)            # digits
        self.assertLessEqual(W, 16)
        for name, tb in tables().items():
            for c in range(0x20, 0x7F):
                self.assertTrue(1 <= want16(tb, c) <= 16)


def build(small, files=None, **kw):
    extra = {}
    key = ('build', small, tuple(files or ()), tuple(sorted((k, repr(v)) for k, v in kw.items())), tuple(sorted(extra.items())))
    if key not in _cache:
        _cache[key] = FP.make_patches(FP.read_extracted, small_prop=small, **kw)
    return _cache[key]


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Isolation(unittest.TestCase):
    def test_only_the_hook_literal_of_option_and_training_differs(self):
        off, roff = build(False)
        on, ron = build(True)
        self.assertEqual(sorted(off), sorted(on))
        self.assertEqual(sorted(ron['small']), sorted(SMALL))
        changed = {k for k in off if off[k] != on[k]}
        self.assertEqual(changed, {'/' + s for s in SMALL} | {'/1ST_READ.BIN'})
        for s in SMALL:
            a, b = off['/' + s], on['/' + s]
            self.assertEqual(len(a), len(b))
            diff = [i for i in range(len(a)) if a[i] != b[i]]
            self.assertTrue(0 < len(diff) <= 4, (s, diff))                         # the 4 byte literal of the advance hook
            h1 = FP.find_sites(FP.read_extracted(s), s)[0]['h1']
            self.assertTrue(all(h1 + 12 <= i < h1 + 16 for i in diff), (s, [hex(i) for i in diff], hex(h1)))
            self.assertEqual(struct.unpack_from('<I', b, h1 + 12)[0], SM)
            self.assertEqual(struct.unpack_from('<I', a, h1 + 12)[0], CAVE)
        for k in off:                                    # EVENT, SCDRF, SEARCH, GAME, NEWS, ... byte identical
            if k not in changed:
                self.assertEqual(off[k], on[k], k)
        for rel in ('/FLOW_PRG/EVENT.BIN', '/FLOW_PRG/SCDRF.BIN', '/FLOW_PRG/SEARCH.BIN', '/FLOW_PRG/GAME.BIN', '/FLOW_PRG/NEWS.BIN', '/FLOW_PRG/G_INCOME.BIN'):
            if rel in off:
                self.assertEqual(off[rel], on[rel], rel)

    def test_1st_read_differs_only_in_the_unused_font_cave_tail(self):
        off, _ = build(False)
        on, _ = build(True)
        a, b = off['/1ST_READ.BIN'], on['/1ST_READ.BIN']
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        lo, hi = CAVE + FP.SMALL_OFF - IMG, CAVE + FP.SMALL_OFF + len(FP.small_bytes(CT)) - IMG
        self.assertTrue(diff and all(lo <= i < hi for i in diff), (hex(min(diff)), hex(max(diff))))
        self.assertFalse(any(a[lo:hi]))                                               # it was zero before
        self.assertEqual(b[lo:hi], FP.small_bytes(CT))
        self.assertEqual(a[CAVE - IMG:CAVE - IMG + FP.CAVE_SIZE], b[CAVE - IMG:CAVE - IMG + FP.CAVE_SIZE])
        self.assertEqual(a[TABLE - IMG:TABLE - IMG + 256], b[TABLE - IMG:TABLE - IMG + 256])

    def test_with_every_other_option(self):
        of = OF.load()
        off, _ = build(False, open_font=of, lin_center=True, align_fix=True, prop_scale=True)
        on, ron = build(True, open_font=of, lin_center=True, align_fix=True, prop_scale=True)
        changed = {k for k in off if off[k] != on[k]}
        self.assertEqual(changed, {'/' + s for s in SMALL} | {'/1ST_READ.BIN'})
        self.assertEqual(sorted(ron['small']), sorted(SMALL))

    def test_custom_file_list(self):
        on, ron = build(True, small_files=['FLOW_PRG/OPTION.BIN'])
        self.assertEqual(ron['small'], ['FLOW_PRG/OPTION.BIN'])

    def test_refusals(self):
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], small_prop=True, place='gap1')
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], small_prop=True, glyphs=False)
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], small_prop=True, variants='ABC')
        k = FP.read_extracted('1ST_READ.BIN')
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(k, bytes([12]) * 256, FP.PLACEMENTS['gap1'], small=True)
        d = FP.read_extracted('FLOW_PRG/OPTION.BIN')
        with self.assertRaises(FP.FontPatchError):
            FP.patch_overlay(d, 'FLOW_PRG/OPTION.BIN', snap=True, small=True)


def pens(img, h1, s, A, x0=20, W=20):
    return [p for p, y in TA.run_layout(img, h1, TA.codes_of(s), W=W, A=A, x0=x0)]


@unittest.skipUnless(HAVE, 'extracted/ missing')
class RealLayoutFunction(unittest.TestCase):
    """the real hooked tsString layout function of the real patched overlay (variant A), window advance 16 like the OPTION list / the Practice panel"""

    def setUp(self):
        self.tab = tables()['open']
        self.of = OF.load()

    def lay(self, rel, small, s, A):
        key = ('lay', rel, small)
        if key not in _cache:
            _cache[key] = FP.make_patches(FP.read_extracted, paths=[rel], open_font=self.of, small_prop=small, small_files=SMALL)
        out, rep = _cache[key]
        img = out['/' + rel]
        h1 = FP.find_sites(FP.read_extracted(rel), rel)[0]['h1']
        k = out['/1ST_READ.BIN']
        o = CAVE - IMG
        ex = [(CAVE, k[o:o + 0x100]), (TABLE, bytes(rep['table']))]
        nat = [(CAVE, CAVE + 0x100)]
        return [p for p, y in TA.run_layout(img, h1, TA.codes_of(s), A=A, W=20, x0=20, extra=ex, native=nat)]

    def expect(self, s, a_scaled):
        pen, out = 20, []
        for ch in s:
            t = self.tab[0] if ch == ' ' else (self.tab[ord(ch)] or 12)
            t = t or 12
            pen += (t * 16 + 12) // 24 if a_scaled else 8
            out.append(pen)
        return out

    def test_panel_and_list_strings(self):
        for rel in SMALL:
            for s in ('Hiroshi Hase', 'Training', 'Advance Schedule', 'BGM', '26 yrs', '0 App 0 G', 'Aichi'):
                self.assertEqual(self.lay(rel, True, s, 16), self.expect(s, True), (rel, s))
                self.assertEqual(self.lay(rel, False, s, 16), self.expect(s, False), (rel, s, 'control'))

    def test_narrow_letters_are_narrower_and_the_line_is_shorter(self):
        for rel in SMALL:
            on, off = self.lay(rel, True, 'Training Illini', 16), self.lay(rel, False, 'Training Illini', 16)
            self.assertLess(on[-1], off[-1])
            self.assertEqual(on, self.expect('Training Illini', True))

    def test_blanks_digits_and_other_windows_are_unchanged(self):
        for rel in SMALL:
            for s in ('        ', '0123456789', '   55   '):
                self.assertEqual(self.lay(rel, True, s, 16), self.lay(rel, False, s, 16), (rel, s))
            for A in (24, 32, 10):
                self.assertEqual(self.lay(rel, True, 'Hiroshi Hase 26', A), self.lay(rel, False, 'Hiroshi Hase 26', A), (rel, A))


if __name__ == '__main__':
    unittest.main(verbosity=1)
