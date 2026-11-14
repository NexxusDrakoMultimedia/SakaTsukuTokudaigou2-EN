#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Tests of --cell-prop (tools/fontpatch.py CELL_SRC / `font.cell`, tools/layoutpatch.py patch_cell_prop, docs/layout-issues.md section 19): the commentary subtitle
line engine of FLOW_PRG/GAME.BIN advances half-width glyphs by the proportional table and drops a blank at the start of a wrapped line.  Nothing starts an
emulator or builds a disc.

    python -I -X utf8 tools/test_cellprop.py

* cave: `cell_adv` assembles (28 bytes at 0x8c2996c0, every word agrees with capstone), the registry claim `font.cell` sits between `font.lin` (0xC0, exactly full)
  and `font.align`, the 64 byte range 0x8c2996c0..0x8c2996ff is zero in the original 1ST_READ.BIN, outside every other claim, not referenced by a single pointer of
  1ST_READ.BIN, GAME.BIN or any FLOW_PRG overlay, and the lin-center cave ends exactly at 0x8c2996c0;
* the REAL half-width and blank blocks of GAME.BIN, patched, run through tools/sh4sim.py with the REAL 1ST_READ cave and BOTH advance tables (the default proportional
  one and the Roboto Condensed Medium one of --open-font): all 94 ASCII codes (0x21..0x7E) at column 0 and at column > 0 write table[code] clamped to 12 (0 -> 12) into the
  advance byte, count one unit, and leave every other memory byte, the column and the registers r5..r15 of the unpatched engine untouched (PR is the engine's own, saved by its prologue); the blank is skipped at
  column 0 (no cell, no unit) and written with the table's blank advance S at column > 0 (S = 12, 7 and the built tables' own value);
* isolation: the GAME.BIN image differs only in the two blocks and the 4 byte literal; the bcast-speed sites 0x4f248 / 0x4f2c6, the OPTIONS records and every other
  byte are those of the other patches, in either order; the 1ST_READ image differs from the cell-prop-off image only in the 28 cave bytes; no other file changes;
* refusals: a patched, foreign, truncated or damaged image, a non-zero literal or cave, a bad cave address, a blank advance outside 1..12, the gap1 placement, no glyphs;
* build wiring: build_patch.apply_prop_font(cell_prop=True) composes on the CURRENT bytes (a bcast-speed patched GAME.BIN keeps its sites), adds a layout report and notes;
  build_patches() refuses --cell-prop without the proportional font / on gap1.
"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontpatch as FP        # noqa: E402
import layoutpatch as LP      # noqa: E402
import moneypatch            # noqa: E402,F401  (registers the money.lib / money.libn claims)
import openfont as OF         # noqa: E402
import patchengine as PE      # noqa: E402
import sh4sim                 # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

HAVE = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN')) and os.path.exists(os.path.join(FP.EXTRACTED, 'FLOW_PRG', 'GAME.BIN'))
BASE = FP.IMG_BASE
GB = LP.CELL_BASE
CAVE = 0x8C2996C0
TABLE = 0x8C299900
HALF_ADDR, SPACE_ADDR, TAIL_ADDR = GB + LP.CELL_HALF, GB + LP.CELL_SPACE, LP.CELL_SPACE_TAIL
LIT_ADDR = LP.CELL_LIT_ADDR
ST, BUF = 0x8C910000, 0x8C920000          # engine state (+4 column, +12 line records) and the character buffer of the simulation
PR_STOP = 0x8C000010
_cache = {}


def game():
    if 'g' not in _cache:
        with open(os.path.join(FP.EXTRACTED, 'FLOW_PRG', 'GAME.BIN'), 'rb') as f:
            _cache['g'] = f.read()
    return _cache['g']


def builds(name):
    """(control 1ST_READ, patched 1ST_READ, table, rep, control files, patched files) of the 'default' or 'open' font"""
    if name not in _cache:
        of = OF.load() if name == 'open' else None
        ctl, rc = FP.make_patches(FP.read_extracted, paths=[], open_font=of, lin_center=True)
        pat, rp = FP.make_patches(FP.read_extracted, paths=[], open_font=of, lin_center=True, cell_prop=True)
        assert rc['table'] == rp['table']
        _cache[name] = (ctl['/1ST_READ.BIN'], pat['/1ST_READ.BIN'], rp['table'], rp, ctl, pat)
    return _cache[name]


def engine_memory(patched, k, table, space=12):
    """sh4sim memory: the engine bytes 0x8c320400..0x8c320560 of GAME.BIN (patched or original), the cave from the patched 1ST_READ, the advance table"""
    g = LP.patch_cell_prop(game(), FP.cell_address(), space) if patched else game()
    mem = {}
    for a in range(0x8C320400, 0x8C320560):
        mem[a] = g[a - GB]
    if patched:
        for a in range(CAVE, CAVE + 0x40):
            mem[a] = k[a - BASE]
    for i, b in enumerate(table):
        mem[TABLE + i] = b
    return mem


def run(mem, start, code, col, rec_line=1, units0=5):
    m = sh4sim.Machine()
    m.mem = dict(mem)
    m.native = [(CAVE, CAVE + 0x40)]
    m.R[14] = ST
    m.R[13] = BUF
    m.R[11] = 82 * rec_line
    m.R[8] = 1
    m.R[4] = col
    m.R[15] = 0x8CF00000
    m.PR = PR_STOP
    m.wn(ST + 4, col, 2)
    m.wn(BUF, code, 2)
    rec = ST + 12 + 82 * rec_line
    m.wn(rec + 1, units0, 1)
    m.run(start, TAIL_ADDR, max_steps=500)
    return m, rec


def mem_diff(a, b, skip=()):
    ks = set(a.mem) | set(b.mem)
    return sorted(x for x in ks if x >= 0x8C900000 and x not in skip and a.mem.get(x, 0) != b.mem.get(x, 0))


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Cave(unittest.TestCase):
    def test_registry(self):
        c = PE.REGISTRY['font.cell']
        self.assertEqual((c.addr, c.size, c.owner, c.placement), (CAVE, 0x40, 'font', 'tail'))
        lin = PE.REGISTRY['font.lin']
        self.assertEqual(lin.end, c.addr)
        self.assertEqual(c.end, PE.REGISTRY.addr('font.align'))
        self.assertEqual(FP.cell_address(), CAVE)
        self.assertEqual(FP.CELL_RESERVE, c.size)
        self.assertEqual(FP.LIN_RESERVE, lin.size)
        self.assertEqual(len(FP.lin_cave_bytes(TABLE)), lin.size)                 # the lin cave fills its claim exactly
        for o in PE.REGISTRY.table():
            if o.name != 'font.cell' and o.placement != 'gap1':
                self.assertFalse(o.overlaps(c.addr, c.size), o)
        tail = [o for o in PE.REGISTRY.table() if o.placement != 'gap1' and o.addr >= 0x8C299400]
        for a, b in zip(tail, tail[1:]):
            self.assertLessEqual(a.end, b.addr, (a, b))

    def test_cave_bytes(self):
        code = FP.cell_cave_bytes(TABLE)
        self.assertEqual(len(code), 28)
        self.assertEqual(struct.unpack('<I', code[-4:])[0], TABLE)
        self.assertLessEqual(len(code), FP.CELL_RESERVE)
        if MD is not None:
            ins = [(i.mnemonic, i.op_str) for i in MD.disasm(code[:-4], CAVE)]
            self.assertEqual([m for m, _ in ins], ['extu.b', 'mov.l', 'mov.b', 'mov', 'cmp/gt', 'bf', 'mov', 'tst', 'bf', 'mov', 'rts', 'nop'])
            self.assertEqual(ins[1][1].split(',')[-1].strip(), 'r1')

    def test_reserve_is_zero_and_unused(self):
        with open(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'), 'rb') as f:
            k = f.read()
        lo = CAVE - BASE
        self.assertEqual(k[lo:lo + 0x40], bytes(0x40))
        # pointers into the range: 1ST_READ.BIN, GAME.BIN and every FLOW_PRG overlay (aligned and unaligned little endian words)
        rng = range(CAVE, CAVE + 0x40)
        files = [os.path.join(FP.EXTRACTED, '1ST_READ.BIN')]
        fp = os.path.join(FP.EXTRACTED, 'FLOW_PRG')
        files += [os.path.join(fp, n) for n in sorted(os.listdir(fp)) if n.upper().endswith('.BIN')]
        hits = []
        for p in files:
            with open(p, 'rb') as f:
                d = f.read()
            for a in rng:
                if struct.pack('<I', a) in d:
                    hits.append((os.path.basename(p), hex(a)))
        self.assertEqual(hits, [])

    def test_lin_center_leaves_the_reserve_alone(self):
        ctl, rc = FP.make_patches(FP.read_extracted, paths=[], lin_center=True)
        k = ctl['/1ST_READ.BIN']
        lo = CAVE - BASE
        self.assertEqual(k[lo:lo + 0x40], bytes(0x40))
        self.assertTrue(any(k[PE.REGISTRY.addr('font.lin') - BASE:lo]))


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Blocks(unittest.TestCase):
    def test_signatures_and_replacement_shape(self):
        g = game()
        self.assertEqual(g[LP.CELL_HALF:LP.CELL_HALF + 22], LP.CELL_HALF_OLD)
        self.assertEqual(g[LP.CELL_SPACE:LP.CELL_SPACE + 30], LP.CELL_SPACE_OLD)
        self.assertEqual(g[LP.CELL_LIT:LP.CELL_LIT + 4], bytes(4))
        self.assertEqual(g.count(LP.CELL_HALF_PRE + LP.CELL_HALF_OLD + LP.CELL_HALF_POST), 1)
        self.assertEqual(g.count(LP.CELL_SPACE_OLD + LP.CELL_SPACE_POST), 1)
        self.assertEqual(len(LP.cell_half_bytes()), 22)
        self.assertEqual(len(LP.cell_space_bytes(7)), 30)
        # the zero literal sits between the 0x8000 mask word and the jump table, and no pc-relative load of the image reads it
        self.assertEqual(g[0x50538:0x5053C], struct.pack('<I', 0x8000))
        readers = []
        for off in range(0, len(g) - 1, 2):
            op = struct.unpack_from('<H', g, off)[0]
            pc = GB + off
            if op >> 12 == 0xD and ((pc + 4) & ~3) + (op & 0xFF) * 4 == LIT_ADDR:
                readers.append(('mov.l', hex(pc)))
            elif op >> 12 == 0x9 and LIT_ADDR - 1 <= pc + 4 + (op & 0xFF) * 2 <= LIT_ADDR + 3:
                readers.append(('mov.w', hex(pc)))
        self.assertEqual(readers, [])

    def test_capstone(self):
        if MD is None:
            self.skipTest('capstone missing')
        h = [(i.mnemonic, i.op_str) for i in MD.disasm(LP.cell_half_bytes(), HALF_ADDR)]
        self.assertEqual([m for m, _ in h][:3], ['mov', 'add', 'add'])
        self.assertIn('jsr', [m for m, _ in h])
        self.assertEqual(h[-1][0], 'mov.b')
        s = [(i.mnemonic, i.op_str) for i in MD.disasm(LP.cell_space_bytes(7), SPACE_ADDR)]
        self.assertEqual(s[0][0], 'tst')
        self.assertEqual(s[1][0], 'bt')
        self.assertIn('0x%x' % TAIL_ADDR, s[1][1])
        self.assertIn(('mov', '#7,r0'), s)

    def test_isolation_of_the_image(self):
        g = game()
        p = LP.patch_cell_prop(g, CAVE, 12)
        self.assertEqual(len(p), len(g))
        diff = [i for i in range(len(g)) if g[i] != p[i]]
        allowed = set(range(LP.CELL_HALF, LP.CELL_HALF + 22)) | set(range(LP.CELL_SPACE, LP.CELL_SPACE + 30)) | set(range(LP.CELL_LIT, LP.CELL_LIT + 4))
        self.assertTrue(diff)
        self.assertTrue(set(diff) <= allowed, [hex(i) for i in diff if i not in allowed])
        self.assertEqual(p[LP.CELL_LIT:LP.CELL_LIT + 4], struct.pack('<I', CAVE))
        self.assertEqual(p[LP.CELL_HALF:LP.CELL_HALF + 22], LP.cell_half_bytes())
        self.assertEqual(p[LP.CELL_SPACE:LP.CELL_SPACE + 30], LP.cell_space_bytes(12))

    def test_other_patches_untouched_in_either_order(self):
        g = game()
        b = LP.patch_bcast_speed(g, '1.9')
        o = LP.patch_options(g, 'GAME')
        for first in ('cell', 'bcast'):
            x = g
            if first == 'cell':
                x = LP.patch_cell_prop(x, CAVE, 12)
                x = LP.patch_options(LP.patch_bcast_speed(x, '1.9'), 'GAME')
            else:
                x = LP.patch_cell_prop(LP.patch_options(LP.patch_bcast_speed(x, '1.9'), 'GAME'), CAVE, 12)
            self.assertEqual(x, LP.patch_cell_prop(LP.patch_options(b, 'GAME'), CAVE, 12))
        c = LP.patch_cell_prop(b, CAVE, 12)
        for site in (0x4F248, 0x4F2C6):                                   # the bcast-speed sites
            self.assertEqual(c[site - 4:site + 12], b[site - 4:site + 12])
            self.assertNotEqual(c[site - 4:site + 12], g[site - 4:site + 12])
        self.assertEqual(LP.patch_cell_prop(o, CAVE, 12)[LP.OPT_SITES['GAME'][1]:LP.OPT_SITES['GAME'][1] + 220], o[LP.OPT_SITES['GAME'][1]:LP.OPT_SITES['GAME'][1] + 220])

    def test_1st_read_isolation(self):
        for name in ('default', 'open'):
            ctl, pat, table, rep, cf, pf = builds(name)
            diff = [i for i in range(len(ctl)) if ctl[i] != pat[i]]
            self.assertTrue(diff and set(diff) <= set(range(CAVE - BASE, CAVE - BASE + 28)), name)     # (the cave has zero bytes of its own)
            self.assertEqual(pat[CAVE - BASE:CAVE - BASE + 28], FP.cell_cave_bytes(TABLE))
            self.assertEqual(sorted(cf), sorted(pf), name)
            for k in cf:
                if k != '/1ST_READ.BIN':
                    self.assertEqual(cf[k], pf[k], name + k)
            self.assertEqual(rep['cell'], CAVE)
            self.assertEqual(rep['cell_space'], FP.cell_space_adv(table))
            self.assertTrue(1 <= rep['cell_space'] <= 12)


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Simulation(unittest.TestCase):
    def half_all(self, name):
        ctl, pat, table, rep, _, _ = builds(name)
        m0 = engine_memory(False, pat, table)
        m1 = engine_memory(True, pat, table)
        bad = []
        for col in (0, 3, 20):
            for c in range(0x21, 0x7F):
                a, rec = run(m0, HALF_ADDR, 0x8000 | c, col)
                b, _ = run(m1, HALF_ADDR, 0x8000 | c, col)
                adv_at = rec + 2 + 2 * col + 1
                want = table[c] if 0 < table[c] <= 12 else 12
                if a.rn(adv_at, 1) != 12 or b.rn(adv_at, 1) != want:
                    bad.append(('adv', chr(c), col, b.rn(adv_at, 1), want))
                if b.rn(rec + 1, 1) != 6 or a.rn(rec + 1, 1) != 6 or b.rn(ST + 4, 2) != col:
                    bad.append(('units/col', chr(c), col))
                if mem_diff(a, b, skip=(adv_at,)):
                    bad.append(('mem', chr(c), col, [hex(x) for x in mem_diff(a, b, skip=(adv_at,))][:4]))
                if [a.R[i] for i in range(5, 16)] != [b.R[i] for i in range(5, 16)]:       # (PR differs by design: the jsr sets it, the engine epilogue restores its own)
                    bad.append(('regs', chr(c), col))
        self.assertEqual(bad, [], name)
        return table

    def test_half_width_default_table(self):
        t = self.half_all('default')
        self.assertTrue(any(t[c] < 12 for c in range(0x21, 0x7F)))

    def test_half_width_open_font_table(self):
        t = self.half_all('open')
        self.assertTrue(any(t[c] > 12 for c in range(0x21, 0x7F)))      # the clamp is exercised (m, w, W ... are 13 px wide in the Roboto table)
        self.assertTrue(any(t[c] < 12 for c in range(0x21, 0x7F)))

    def test_half_width_kana_slots_and_unlisted(self):
        """codes 0xA1..0xDF and an unlisted code (table 0) use the same rule"""
        ctl, pat, table, rep, _, _ = builds('default')
        m1 = engine_memory(True, pat, table)
        for c in list(range(0xA1, 0xE0)) + [0x21]:
            b, rec = run(m1, HALF_ADDR, 0x8000 | c, 2)
            want = table[c] if 0 < table[c] <= 12 else 12
            self.assertEqual(b.rn(rec + 2 + 4 + 1, 1), want, hex(c))
        zero = bytearray(table)
        zero[0x41] = 0
        zero[0x42] = 24
        m2 = engine_memory(True, pat, bytes(zero))
        self.assertEqual(run(m2, HALF_ADDR, 0x8041, 1)[0].rn(ST + 12 + 82 + 2 + 2 + 1, 1), 12)     # unlisted -> 12
        self.assertEqual(run(m2, HALF_ADDR, 0x8042, 1)[0].rn(ST + 12 + 82 + 2 + 2 + 1, 1), 12)     # 24 -> clamp 12

    def test_blank(self):
        for name in ('default', 'open'):
            ctl, pat, table, rep, _, _ = builds(name)
            for space in sorted({12, 7, 1, rep['cell_space']}):
                m0 = engine_memory(False, pat, table)
                m1 = engine_memory(True, pat, table, space)
                for col in (0, 1, 4, 20, 38):
                    a, rec = run(m0, SPACE_ADDR, 0x8020, col)
                    b, _ = run(m1, SPACE_ADDR, 0x8020, col)
                    adv_at = rec + 2 + 2 * col + 1
                    self.assertEqual(a.rn(adv_at, 1), 12)
                    self.assertEqual(a.rn(rec + 1, 1), 6)
                    if col == 0:
                        self.assertEqual(b.rn(adv_at, 1), 0, (name, space))             # nothing written: the cell of a fresh record keeps advance 0
                        self.assertEqual(b.rn(rec + 1, 1), 5, 'no unit counted for the dropped blank')
                        self.assertEqual(mem_diff(b, run(m1, SPACE_ADDR, 0x8020, 0, units0=5)[0]), [])
                    else:
                        self.assertEqual(b.rn(adv_at, 1), space, (name, space, col))
                        self.assertEqual(b.rn(rec + 1, 1), 6)
                        self.assertEqual(mem_diff(a, b, skip=(adv_at,)), [])
                    self.assertEqual(b.rn(ST + 4, 2), col)
                    self.assertEqual([a.R[i] for i in range(5, 16)], [b.R[i] for i in range(5, 16)])

    def test_blank_col0_flow_with_stale_cell(self):
        """a record is zero filled by the line advance (0x8c3201fe), so the skipped cell of column 0 has flag 0 and advance 0; the display loop adds 0 px"""
        ctl, pat, table, rep, _, _ = builds('default')
        m1 = engine_memory(True, pat, table)
        b, rec = run(m1, SPACE_ADDR, 0x8020, 0)
        self.assertEqual(b.rn(rec + 2, 2), 0)
        # the common tail (column + 1, glyph count + 1) runs after the skip
        b.run(TAIL_ADDR, 0x8C320510, max_steps=50)
        self.assertEqual(b.rn(ST + 4, 2), 1)
        self.assertEqual(b.rn(rec, 1), 1)


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Refusals(unittest.TestCase):
    def raises(self, fn, text):
        with self.assertRaises(LP.LayoutPatchError) as cm:
            fn()
        self.assertIn(text, str(cm.exception))

    def test_second_application(self):
        p = LP.patch_cell_prop(game(), CAVE, 12)
        self.raises(lambda: LP.patch_cell_prop(p, CAVE, 12), 'already patched')
        p7 = LP.patch_cell_prop(game(), CAVE, 7)
        self.raises(lambda: LP.patch_cell_prop(p7, CAVE, 7), 'already patched')

    def test_foreign_and_damaged(self):
        g = bytearray(game())
        for off in (LP.CELL_HALF - 12, LP.CELL_HALF + 3, LP.CELL_HALF + 21, LP.CELL_HALF + 22 + 5, LP.CELL_SPACE + 1, LP.CELL_SPACE + 29, LP.CELL_SPACE + 30 + 2):
            x = bytearray(g)
            x[off] ^= 0x04
            self.raises(lambda: LP.patch_cell_prop(bytes(x), CAVE, 12), 'was found 0 times')
        self.raises(lambda: LP.patch_cell_prop(bytes(g[:LP.CELL_SPACE + 10]), CAVE, 12), 'was found 0 times')
        self.raises(lambda: LP.patch_cell_prop(b'', CAVE, 12), 'was found 0 times')
        self.raises(lambda: LP.patch_cell_prop(bytes(len(g)), CAVE, 12), 'was found 0 times')

    def test_literal_and_arguments(self):
        g = bytearray(game())
        g[LP.CELL_LIT] = 1
        self.raises(lambda: LP.patch_cell_prop(bytes(g), CAVE, 12), 'not zero')
        for bad in (0, -1, 13, 24):
            self.raises(lambda: LP.patch_cell_prop(game(), CAVE, bad), 'blank advance')
        for bad in (CAVE + 2, 0x8C000000, 0x8C2D0000, 0, 0x8C910000):
            self.raises(lambda: LP.patch_cell_prop(game(), bad, 12), 'resident image')

    def test_font_side(self):
        with open(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'), 'rb') as f:
            k = bytearray(f.read())
        table = bytes([12]) * 256
        FP.patch_1st_read(bytes(k), table, cell=True)
        k[CAVE - BASE + 0x3F] = 1                                          # the last byte of the reserve
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(bytes(k), table, cell=True)
        k[CAVE - BASE + 0x3F] = 0
        FP.patch_1st_read(bytes(k), table, cell=True)                      # fine again
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(bytes(k), table, 'gap1', cell=True)
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], place='gap1', cell_prop=True)
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], glyphs=False, cell_prop=True)
        once = FP.patch_1st_read(bytes(k), table, cell=True)
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(once, table, cell=True)                      # the reserve is no longer zero: refused

    def test_space_adv_rule(self):
        self.assertEqual([FP.cell_space_adv(bytes([s]) + bytes(255)) for s in (0, 1, 7, 12, 13, 24)], [12, 1, 7, 12, 12, 12])


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Wiring(unittest.TestCase):
    def test_apply_prop_font_composes_on_current_bytes(self):
        import build_patch as BP
        res = BP.Result()
        b = LP.patch_bcast_speed(game(), '1.9')
        res.patches['/FLOW_PRG/GAME.BIN'] = b
        BP.apply_prop_font(res, os.path.join(BP.ROOT, 'translation', 'font'), cell_prop=True, lin_center=True)
        g = res.patches['/FLOW_PRG/GAME.BIN']
        self.assertEqual(g[0x4F244:0x4F254], b[0x4F244:0x4F254])           # the bcast-speed gate is still there
        self.assertEqual(g[LP.CELL_LIT:LP.CELL_LIT + 4], struct.pack('<I', CAVE))
        self.assertEqual(g[LP.CELL_HALF:LP.CELL_HALF + 22], LP.cell_half_bytes())
        self.assertTrue(any('cell-prop' in n for n in res.notes))
        self.assertTrue(any(f.iso == '/FLOW_PRG/GAME.BIN' and f.kind == 'layout' and any('cell_adv' in n for n in f.notes) for f in res.files))
        k = res.patches['/1ST_READ.BIN']
        self.assertEqual(k[CAVE - BASE:CAVE - BASE + 28], FP.cell_cave_bytes(TABLE))
        # off: GAME.BIN keeps the engine blocks
        res2 = BP.Result()
        res2.patches['/FLOW_PRG/GAME.BIN'] = b
        BP.apply_prop_font(res2, os.path.join(BP.ROOT, 'translation', 'font'), lin_center=True)
        self.assertEqual(res2.patches['/FLOW_PRG/GAME.BIN'][LP.CELL_HALF:LP.CELL_HALF + 22], LP.CELL_HALF_OLD)
        self.assertEqual(res2.patches['/1ST_READ.BIN'][CAVE - BASE:CAVE - BASE + 0x40], bytes(0x40))

    def test_second_application_stops_the_build(self):
        import build_patch as BP
        res = BP.Result()
        res.patches['/FLOW_PRG/GAME.BIN'] = LP.patch_cell_prop(game(), CAVE, 12)
        with self.assertRaises(BP.PipelineError) as cm:
            BP.apply_prop_font(res, os.path.join(BP.ROOT, 'translation', 'font'), cell_prop=True)
        self.assertIn('cell', str(cm.exception))

    def test_build_patches_validation(self):
        import build_patch as BP
        for kw, text in (({'prop_font': False}, '--proportional-font on'), ({'prop_font': True, 'prop_glyphs': False}, '--proportional-font on'),
                         ({'prop_font': True, 'prop_place': 'gap1'}, 'tail')):
            with self.assertRaises(BP.PipelineError) as cm:
                BP.build_patches(os.path.join(BP.ROOT, 'translation'), cell_prop=True, **kw)
            self.assertIn('--cell-prop', str(cm.exception))
            self.assertIn(text, str(cm.exception))

    def test_check_flag_combos(self):
        import argparse
        import build_patch as BP
        a = argparse.Namespace(open_font='off', small_prop='off', lin_center='off', align_fix='off', cell_prop='on', proportional_font='off',
                               prop_font_place='tail', prop_font_variants='A')
        self.assertIn('--cell-prop on needs --proportional-font on', BP.check_flag_combos(a))
        a.proportional_font = 'control'
        self.assertIn('--proportional-font on', BP.check_flag_combos(a))
        a.proportional_font, a.prop_font_place = 'on', 'gap1'
        self.assertIn('--prop-font-place tail', BP.check_flag_combos(a))
        a.prop_font_place = 'tail'
        self.assertIsNone(BP.check_flag_combos(a))
        a.cell_prop = 'off'
        a.proportional_font = 'off'
        self.assertIsNone(BP.check_flag_combos(a))


if __name__ == '__main__':
    unittest.main(verbosity=1)
