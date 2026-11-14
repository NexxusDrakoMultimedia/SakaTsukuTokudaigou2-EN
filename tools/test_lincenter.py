#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Tests of --lin-center (tools/fontpatch.py LIN_SRC, docs/layout-issues.md section 16): narrow half-width glyphs are centred in their 12 px tile by
the linear text writer FUN_8c15e9c6 of 1ST_READ.BIN.  Nothing starts an emulator.

    python -I -X utf8 tools/test_lincenter.py

* the cave assembles (192 bytes = its whole 0xC0 claim), every word agrees with capstone, the claim `font.lin` sits between money.lib and font.cell;
* the patched image differs from the lin-center-off image only in the 42 hook bytes and the cave; the hook is signature located; patched, foreign,
  truncated, non-zero-cave and gap1 inputs are refused;
* the REAL writer from the patched 1ST_READ with the REAL FONT.BIN glyphs, for BOTH advance tables (the default proportional one and the Roboto
  Condensed Medium one of --open-font), for all 158 half-width codes (0x20..0x7E, 0xA1..0xDF): equals a Python reference shift, wide / zero-advance /
  k = 0 glyphs are byte-identical to the control, no ink pixel is lost (the k rightmost columns of the source glyph are paper), the registers the
  writer keeps (r4-r6, r8-r15, PR) and every memory byte outside the 12 x 24 destination are those of the control;
* the strings of the match intro and the OPTIONS rows (Stadium, Cloudy, KICK OFF, OPTIONS, Subtitles, Near/Mid/Far): per-cell result equals the
  reference, the gaps behind i / l shrink and no cell loses ink.
"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font as F              # noqa: E402
import fontpatch as FP        # noqa: E402
import moneypatch            # noqa: E402,F401  (registers the money.lib / money.libn claims)
import openfont as OF         # noqa: E402
import patchengine as PE      # noqa: E402
import sh4sim                 # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

HAVE = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'))
BASE = FP.IMG_BASE
WRITER = 0x8C15E9C6
CAVE = 0x8C299600
SITE = 0x8C15EA22
DEST = 0x8C900000
HALF_CODES = list(range(0x20, 0x7F)) + list(range(0xA1, 0xE0))

_cache = {}


def builds(name):
    """(control 1ST_READ, patched 1ST_READ, FONT.BIN bytes, table, rep) of the 'default' or 'open' font; control = same build without lin_center"""
    if name not in _cache:
        of = OF.load() if name == 'open' else None
        ctl, rc = FP.make_patches(FP.read_extracted, paths=[], open_font=of)
        pat, rp = FP.make_patches(FP.read_extracted, paths=[], open_font=of, lin_center=True)
        assert rc['table'] == rp['table']
        _cache[name] = (ctl['/1ST_READ.BIN'], pat['/1ST_READ.BIN'], pat['/FONT.BIN'], rp['table'], rp, ctl, pat)
    return _cache[name]


def machine(image, font_bytes, table):
    """sh4sim memory holding the writer, the cave, the table and the half-width glyph array (the pointer at 0x8c22837C)"""
    m = sh4sim.Machine()
    mem = {}
    for a in range(0x8C15E900, 0x8C15EC00):
        mem[a] = image[a - BASE]
    for a in range(CAVE, CAVE + 0x100):
        mem[a] = image[a - BASE]
    tbl = FP.PLACEMENTS['tail'][1]
    for i, b in enumerate(table):
        mem[tbl + i] = b
    half = F.Font(font_bytes).tail
    hb = 0x8C800000
    for i, b in enumerate(half):
        mem[hb + i] = b
    for i, b in enumerate(struct.pack('<I', hb)):
        mem[0x8C22837C + i] = b
    m.mem = mem
    m.native = [(CAVE, CAVE + 0x100)]
    return m, half


def run_glyph(base_m, byte, cells=1):
    """the real writer for one half-width code; returns (24 rows x 6 bytes, machine) (destination row pitch 12 * cells)"""
    m = sh4sim.Machine()
    m.mem = dict(base_m.mem)
    m.native = list(base_m.native)
    for i in range(24 * 12 * cells + 64):
        m.mem[DEST + i] = 0xAA
    m.R[4] = DEST
    m.R[5] = 0x8000 | byte
    m.R[6] = cells
    m.R[15] = 0x8CF00000
    m.PR = 0x8C000010
    m.run(WRITER, 0x8C000010, max_steps=20000)
    rows = [m.rn(DEST + r * 12 * cells, 6).to_bytes(6, 'little') for r in range(24)]
    return rows, m


def nibs(row):
    return [x for b in row for x in (b >> 4, b & 15)]


def shift_ref(g, k):
    out = bytearray()
    for r in range(24):
        n = nibs(g[r * 6:r * 6 + 6])
        n = [15] * k + n[:12 - k]
        out += bytes((n[i] << 4) | n[i + 1] for i in range(0, 12, 2))
    return bytes(out)


def lost_ink(g, k):
    """True if one of the k rightmost columns of the 12 px glyph holds a non-paper nibble (it would be shifted out of the tile)"""
    return any(x != 15 for r in range(24) for x in nibs(g[r * 6:r * 6 + 6])[12 - k:])


def ink_cols(rows):
    cols = [c for c in range(12) if any(nibs(r)[c] != 15 for r in rows)]
    return (cols[0], cols[-1]) if cols else None


@unittest.skipUnless(HAVE, 'extracted/1ST_READ.BIN missing')
class CaveAndHook(unittest.TestCase):
    def test_registry_and_size(self):
        c = PE.REGISTRY['font.lin']
        self.assertEqual((c.addr, c.size, c.owner, c.placement), (CAVE, 0xC0, 'font', 'tail'))
        self.assertEqual(c.end, PE.REGISTRY.addr('font.cell'))             # the 64 spare bytes behind the cave are the --cell-prop claim
        self.assertEqual(PE.REGISTRY['font.cell'].end, PE.REGISTRY.addr('font.align'))
        self.assertGreaterEqual(c.addr, PE.REGISTRY.addr('money.lib') + PE.REGISTRY.size('money.lib'))
        code = FP.lin_cave_bytes(FP.PLACEMENTS['tail'][1])
        self.assertEqual(len(code), 192)
        self.assertLessEqual(len(code), FP.LIN_RESERVE)
        self.assertEqual(FP.LIN_RESERVE, PE.REGISTRY.size('font.lin'))
        self.assertEqual(FP.lin_address(), CAVE)

    def test_capstone_words(self):
        if MD is None:
            self.skipTest('capstone missing')
        code = FP.lin_cave_bytes(FP.PLACEMENTS['tail'][1])
        words = [code[i:i + 2] for i in range(0, len(code) - 4, 2)]       # the last 4 bytes are the table literal
        n = 0
        for i in MD.disasm(code[:len(code) - 4], CAVE):
            n += 1
            self.assertNotEqual(i.mnemonic, '.byte')
        self.assertGreater(n, 60)
        self.assertEqual(struct.unpack('<I', code[-4:])[0], FP.PLACEMENTS['tail'][1])
        self.assertTrue(words)

    def test_hook_bytes(self):
        h = FP.lin_hook_bytes()
        self.assertEqual(len(h), 42)
        self.assertEqual(struct.unpack('<I', h[10:14])[0], CAVE)
        self.assertEqual(h[14:], b'\x09\x00' * 14)
        self.assertEqual(FP.LIN_SITE + BASE, SITE)
        if MD:
            ops = [(i.mnemonic, i.op_str) for i in MD.disasm(h[:10], SITE)]
            self.assertEqual([o[0] for o in ops], ['mov.l', 'jsr', 'nop', 'bra', 'nop'])

    def test_site_unique_and_expected_bytes(self):
        k = FP.read_extracted('1ST_READ.BIN')
        self.assertEqual(FP.lin_find_site(k), SITE - BASE)
        self.assertEqual(k[SITE - BASE:SITE - BASE + 42], FP.LIN_OLD)
        self.assertEqual(k.count(FP.LIN_BEFORE + FP.LIN_OLD + FP.LIN_AFTER), 1)
        self.assertFalse(any(k[CAVE - BASE:CAVE - BASE + 0x100]), 'cave range must be zero in the original image')

    def test_lin_k_matches_rule(self):
        self.assertEqual([FP.lin_k(a) for a in (0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 24)], [0, 6, 5, 4, 4, 3, 3, 2, 1, 1, 0, 0, 0])


@unittest.skipUnless(HAVE, 'extracted/1ST_READ.BIN missing')
class Isolation(unittest.TestCase):
    def check(self, name):
        ctl, pat, _, table, rep, ctl_out, pat_out = builds(name)
        self.assertEqual(len(ctl), len(pat))
        diff = [i for i in range(len(ctl)) if ctl[i] != pat[i]]
        hook = set(range(SITE - BASE, SITE - BASE + 42))
        cave = set(range(CAVE - BASE, CAVE - BASE + 192))
        self.assertTrue(set(diff) <= hook | cave)
        self.assertTrue(any(i in hook for i in diff) and any(i in cave for i in diff))
        # everything else of the build is the same files, byte for byte
        self.assertEqual(sorted(ctl_out), sorted(pat_out))
        for p in ctl_out:
            if p != '/1ST_READ.BIN':
                self.assertEqual(ctl_out[p], pat_out[p], p)
        self.assertEqual(rep['lin'], CAVE)
        self.assertEqual(pat[CAVE - BASE + 192:CAVE - BASE + 0x100], bytes(0x100 - 192))

    def test_default_font(self):
        self.check('default')

    def test_open_font(self):
        self.check('open')

    def test_vs_original_image(self):
        """against the ORIGINAL 1ST_READ: lin-center adds only hook + cave to the proportional font's edits"""
        ctl, pat, *_ = builds('default')
        orig = FP.read_extracted('1ST_READ.BIN')
        d_c = {i for i in range(len(orig)) if orig[i] != ctl[i]}
        d_p = {i for i in range(len(orig)) if orig[i] != pat[i]}
        self.assertTrue(d_c < d_p)
        extra = d_p - d_c
        self.assertTrue(all(SITE - BASE <= i < SITE - BASE + 42 or CAVE - BASE <= i < CAVE - BASE + 192 for i in extra))


@unittest.skipUnless(HAVE, 'extracted/1ST_READ.BIN missing')
class Refusals(unittest.TestCase):
    def test_patched_image(self):
        _, pat, *_ = builds('default')
        with self.assertRaises(FP.FontPatchError) as cm:
            FP.lin_find_site(pat)
        self.assertIn('already patched', str(cm.exception))
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(pat, builds('default')[3], lin=True)

    def test_foreign_image(self):
        k = bytearray(FP.read_extracted('1ST_READ.BIN'))
        k[SITE - BASE + 10] ^= 1
        with self.assertRaises(FP.FontPatchError):
            FP.lin_find_site(bytes(k))
        k = bytearray(FP.read_extracted('1ST_READ.BIN'))
        k[SITE - BASE - 2] ^= 1                                          # the `add r3,r6` neighbour
        with self.assertRaises(FP.FontPatchError):
            FP.lin_find_site(bytes(k))
        k = bytearray(FP.read_extracted('1ST_READ.BIN'))
        k[SITE - BASE + 42] ^= 1                                         # `add r6,r14`
        with self.assertRaises(FP.FontPatchError):
            FP.lin_find_site(bytes(k))

    def test_truncated(self):
        k = FP.read_extracted('1ST_READ.BIN')
        with self.assertRaises(FP.FontPatchError):
            FP.lin_find_site(k[:SITE - BASE + 20])
        with self.assertRaises(FP.FontPatchError):
            FP.lin_find_site(b'')

    def test_moved_site(self):
        """a copy of the loop body somewhere else (and the real one damaged) is refused: the hook is built for one address"""
        k = bytearray(FP.read_extracted('1ST_READ.BIN'))
        sig = bytes(k[SITE - BASE - 2:SITE - BASE + 50])
        k[SITE - BASE - 2:SITE - BASE + 50] = bytes(52)
        k[0x1000:0x1000 + len(sig)] = sig
        with self.assertRaises(FP.FontPatchError) as cm:
            FP.lin_find_site(bytes(k))
        self.assertIn('expected', str(cm.exception))

    def test_nonzero_cave(self):
        k = bytearray(FP.read_extracted('1ST_READ.BIN'))
        k[CAVE - BASE + 0x80] = 1
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(bytes(k), builds('default')[3], lin=True)

    def test_gap1_and_no_glyphs(self):
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], place='gap1', lin_center=True)
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], glyphs=False, lin_center=True)

    def test_off_is_untouched(self):
        ctl, *_ = builds('default')
        self.assertEqual(ctl[SITE - BASE:SITE - BASE + 42], FP.LIN_OLD)
        self.assertFalse(any(ctl[CAVE - BASE:CAVE - BASE + 0x100]))


@unittest.skipUnless(HAVE, 'extracted/1ST_READ.BIN missing')
class Writer(unittest.TestCase):
    def check_font(self, name):
        ctl, pat, fnt, table, rep, *_ = builds(name)
        mc, half = machine(ctl, fnt, table)
        mp, _ = machine(pat, fnt, table)
        changed = bad = 0
        for b in HALF_CODES:
            idx = F.half_index(b)
            g = half[idx * 144:(idx + 1) * 144]
            rc, c_m = run_glyph(mc, b)
            rp, p_m = run_glyph(mp, b)
            c, p = b''.join(rc), b''.join(rp)
            self.assertEqual(c, g, 'control copies the glyph unchanged: %#x' % b)
            k = FP.lin_k(table[b])
            self.assertEqual(p, shift_ref(g, k), '%s %#x (advance %d, k %d)' % (name, b, table[b], k))
            if k == 0:
                self.assertEqual(p, g, 'k = 0 / wide / unlisted glyph must be unchanged: %#x' % b)
            else:
                changed += 1
            self.assertFalse(lost_ink(g, k), '%s %#x: the shift would push ink out of the tile (advance %d, k %d)' % (name, b, table[b], k))
            # every register the writer keeps and every memory byte outside the destination equal the control's
            for r in [4, 5, 6] + list(range(8, 16)):
                self.assertEqual(p_m.R[r], c_m.R[r], 'r%d after %#x' % (r, b))
            self.assertEqual(p_m.PR, c_m.PR)
            keys = set(c_m.mem) | set(p_m.mem)
            for a in keys:
                if DEST <= a < DEST + 24 * 12 + 64 or 0x8C15E900 <= a < 0x8C15EC00 or CAVE <= a < CAVE + 0x100:
                    continue        # destination and the code image (hook + cave differ by construction)
                self.assertEqual(c_m.mem.get(a), p_m.mem.get(a), 'memory %#x after %#x' % (a, b))
            bad += 0
        self.assertGreater(changed, 25)
        return changed

    def test_default_table(self):
        self.assertGreater(self.check_font('default'), 25)

    def test_roboto_table(self):
        n = self.check_font('open')
        self.assertGreater(n, 25)

    def test_roboto_zero_advance_and_wide(self):
        """unlisted (advance 0) codes and the glyphs wider than 12 px advance stay as they are, in the Roboto table"""
        ctl, pat, fnt, table, rep, *_ = builds('open')
        mc, half = machine(ctl, fnt, table)
        mp, _ = machine(pat, fnt, table)
        wide = [b for b in HALF_CODES if table[b] >= 12]
        zero = [b for b in HALF_CODES if table[b] == 0]
        self.assertGreater(len(wide), 40)
        for b in wide + zero:
            self.assertEqual(b''.join(run_glyph(mp, b)[0]), b''.join(run_glyph(mc, b)[0]), hex(b))

    def test_two_cells(self):
        """a 2 cell call (row pitch 24) behaves the same: the cave only fills its own 6 bytes per row"""
        ctl, pat, fnt, table, rep, *_ = builds('default')
        mc, half = machine(ctl, fnt, table)
        mp, _ = machine(pat, fnt, table)
        for b in (ord('i'), ord('l'), ord('A')):
            rp, _m = run_glyph(mp, b, cells=2)
            rc, _m = run_glyph(mc, b, cells=2)
            g = b''.join(rc)
            self.assertEqual(b''.join(rp), shift_ref(g, FP.lin_k(table[b])))

    STRINGS = ('Stadium', 'Cloudy', 'KICK OFF', 'OPTIONS', 'Subtitles', 'Near/Mid/Far', 'Commentary', 'Kill il Ill!')

    def test_strings(self):
        for name in ('default', 'open'):
            ctl, pat, fnt, table, rep, *_ = builds(name)
            mc, half = machine(ctl, fnt, table)
            mp, _ = machine(pat, fnt, table)
            for s in self.STRINGS:
                for ch in s:
                    b = ord(ch)
                    rc = run_glyph(mc, b)[0]
                    rp = run_glyph(mp, b)[0]
                    k = FP.lin_k(table[b])
                    self.assertEqual(b''.join(rp), shift_ref(b''.join(rc), k), '%s %r' % (name, ch))
                    if ch != ' ':
                        ic, ip = ink_cols(rc), ink_cols(rp)
                        if ic:
                            self.assertEqual(ip, (ic[0] + k, ic[1] + k), '%s %r ink columns' % (name, ch))
                            self.assertLessEqual(ip[1], 11)
            # the gap behind a narrow glyph: the pixels between the ink of 'i' and the ink of the next glyph's cell edge
            for ch in 'il':
                ic = ink_cols(run_glyph(mc, ord(ch))[0])
                ip = ink_cols(run_glyph(mp, ord(ch))[0])
                gap_ctl_right = 11 - ic[1]
                gap_pat_right = 11 - ip[1]
                self.assertLess(gap_pat_right, gap_ctl_right, '%s %r: right gap must shrink' % (name, ch))
                self.assertLessEqual(abs(ip[0] - (11 - ip[1])), 1, '%s %r: centred within 1 px' % (name, ch))

    def test_roboto_centre_error(self):
        """with the Roboto table every glyph with k > 0 ends up within 1 px of the exact centre of its 12 px tile"""
        ctl, pat, fnt, table, rep, *_ = builds('open')
        mc, half = machine(ctl, fnt, table)
        mp, _ = machine(pat, fnt, table)
        worst = 0
        for b in range(0x21, 0x7F):
            ip = ink_cols(run_glyph(mp, b)[0])
            if ip is None or FP.lin_k(table[b]) == 0:
                continue
            err = abs(ip[0] - (11 - ip[1]))               # left margin - right margin (2 x centre error)
            worst = max(worst, err)
            self.assertLessEqual(err, 2, '%r: left margin %d, right margin %d' % (chr(b), ip[0], 11 - ip[1]))
        self.assertLessEqual(worst, 2)


if __name__ == '__main__':
    unittest.main(verbosity=1)
