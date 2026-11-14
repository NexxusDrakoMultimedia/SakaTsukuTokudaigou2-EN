"""Tests of the alignment fix (tools/fontpatch.py ALIGN_SRC, docs/layout-issues.md section 10).  Nothing starts an emulator.

    python -I -X utf8 tools/test_alignfix.py

* the align cave assembles, every word agrees with capstone, it fits its registered reserve; the font cave is byte-identical with and without the
  fix (stage 8h: the snap is entered only through the hook literal of the overlays in ALIGN_SNAP_FILES, see tools/test_align_isolation.py);
* the REAL layout function of the REAL PLNUMSET overlay (patched by make_patches(align_fix=True)) executed in tools/sh4sim.py: the
  shirt-number column lands on the same pixel for names of every width, single word spaces keep their advance, the control (align off)
  is ragged;
* `pw3` (the strlen replacement) executed against a Python reference over many strings, and over the strings of the player-card panel;
* the player-card panel of CAP_SLCT / ENDOPT / EVENT: 20 idioms and 8 strlen pools found, 18 idioms patched (the 2 SALARY idioms keep their
  `shll2`: their setter returns a character count, not a pw3), the idiom arithmetic executed from the patched bytes (x = anchor - 3 * len3,
  salary x = anchor - 12 * len), and the end of the REAL laid-out text of Tokyo / Season / Average ... lies within 2 px of the anchor;
  the REAL salary setter + money cave executed in the simulator puts the end of `1400 man` within 3 px of the anchor (class Salary);
* signature checks: a patched or foreign image is refused.
"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontcheck as FC       # noqa: E402
import fontpatch as FP       # noqa: E402
import patchengine as PE     # noqa: E402
import sh4sim                # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

HAVE = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'))
PANELS = ['FLOW_PRG/CAP_SLCT.BIN', 'FLOW_PRG/ENDOPT.BIN', 'FLOW_PRG/EVENT.BIN']
BASE = 0x8C2D0000
ALIGN = 0x8C299700
CT = FP.placement()

_cache = {}


def built():
    """make_patches(align_fix=True) (the default mode: snap in PLNUMSET, panel edits) over the files the tests use (cached)"""
    if 'b' not in _cache:
        paths = ['FLOW_PRG/PLNUMSET.BIN', 'FLOW_PRG/MEETING.BIN'] + PANELS
        out, rep = FP.make_patches(FP.read_extracted, paths=paths, align_fix='default')
        ctl, _ = FP.make_patches(FP.read_extracted, paths=paths, align_fix=False)
        _cache['b'] = (out, rep, ctl)
    return _cache['b']


def built_all():
    """the same with the snap in EVERY hooked overlay (mode 'snap-all', the stage 8b wiring): used where the tests lay out text with MEETING's
    layout function; the control is the align-off build"""
    if 'a' not in _cache:
        paths = ['FLOW_PRG/PLNUMSET.BIN', 'FLOW_PRG/MEETING.BIN'] + PANELS
        out, rep = FP.make_patches(FP.read_extracted, paths=paths, align_fix='snap-all')
        _cache['a'] = (out, rep, built()[2])
    return _cache['a']


def table():
    return built()[1]['table']


def run_layout(img, h1, codes, W=20, A=24, flag=1, x0=20, y0=240, lh=24, extra=(), native=(), n22=None, cnt=None):
    """the real layout function (variant A) on `codes`; window +0x22 (code count) is set, unlike fontcheck.run_layout.
    returns [(pen after code i, y)]"""
    p = FC.VAR['A']
    m = sh4sim.Machine()
    m.load(BASE, img)
    for a, d in extra:
        m.load(a, d)
    m.native = [(BASE, BASE + len(img))] + list(native)
    win = 0x8D000000 - 0x4000
    arr = win + 0x800
    for i, c in enumerate(codes):
        m.wn(arr + 2 * i, c, 2)
    m.wn(win + p['ptr'], arr, 4)
    m.wn(win + p['cnt'], len(codes) if cnt is None else cnt, 2)
    m.wn(win + 0x22, len(codes) if n22 is None else n22, 2)
    m.wn(win + p['W'], W, 1)
    m.wn(win + p['adv'], A & 0xFF, 1)
    m.wn(win + p['LH'], lh, 1)
    m.wn(win + p['F'], flag, 1)
    m.wn(win + p['X0'], x0, 2)
    m.wn(win + p['Y0'], y0, 2)
    m.wn(win + 56, 0x20, 4)
    m.R[4] = win
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    join = BASE + h1 + 0x1A
    snaps = []
    m.run(BASE + FC.func_range(img, h1), 0x8C000000,
          watch={join: lambda mm: snaps.append((sh4sim.s32(mm.R[p['pen']]), sh4sim.s32(mm.R[8])))}, max_steps=2000000)
    return snaps


def codes_of(s):
    return [0x2020 if ch == ' ' else 0x8000 | ord(ch) for ch in s]


def h1_of(rel):
    d = FP.read_extracted(rel)
    return d, FP.find_sites(d, rel)[0]['h1']


def caves(tbl, align=True):
    ex = [(CT[0], FP.cave_bytes(CT)), (CT[1], tbl)]
    nat = [(CT[0], CT[0] + 0x100)]
    if align:
        ex.append((ALIGN, FP.align_bytes(ALIGN, CT[1])))
        nat.append((ALIGN, ALIGN + 0x100))
    return ex, nat


def pen_of(table_, s):
    """independent model: pixel width of an ASCII string with the table"""
    return sum((table_[0] if ch == ' ' else table_[ord(ch)] or 12) for ch in s)


# ------------------------------------------------------------------------------------------------ the cave
class AlignCave(unittest.TestCase):
    def test_assembles_and_agrees_with_capstone(self):
        code, sym = FP.align_assembly(ALIGN, CT[1])
        self.assertLessEqual(len(code), FP.ALIGN_RESERVE)
        self.assertEqual(PE.REGISTRY.size('font.align'), FP.ALIGN_RESERVE)
        self.assertEqual(PE.REGISTRY.addr('font.align'), ALIGN)
        import sh4asm2
        a = sh4asm2.Asm(ALIGN, {'TABLE': CT[1], 'CAVE': CT[0]}).parse(FP.ALIGN_SRC)
        items = a.assemble()
        n = 0
        if MD is not None:
            for addr, wb, text in items:
                if len(wb) != 2 or text.startswith('.'):
                    continue
                if addr in (sym['c2020'], sym['inv3']):
                    continue
                ins = list(MD.disasm(wb, addr))
                self.assertTrue(ins, '%08x %s undecodable' % (addr, wb.hex()))
                got = ('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip()
                self.assertEqual(got, text, '%08x' % addr)
                n += 1
            self.assertGreater(n, 90)

    def test_font_cave_is_untouched(self):
        for scale in (False, True):
            base = FP.cave_bytes(CT, scale)
            self.assertEqual(len(base), FP.CAVE_SIZE_SCALE if scale else FP.CAVE_SIZE)
            self.assertEqual(base[FP.ADV_RET_OFF:FP.ADV_RET_OFF + 4], bytes.fromhex('0b000900'))      # the table path still ends in `rts ; nop`
        self.assertEqual(FP.cave_bytes(CT), FP._CAVE[:-4] + struct.pack('<I', CT[1]))                  # default build: byte identical

    def test_entry_is_the_hook_literal_only(self):
        d, h1 = h1_of('FLOW_PRG/PLNUMSET.BIN')
        std, snap = FP.hook_h1('A', CT), FP.hook_h1('A', CT, ALIGN)
        self.assertEqual(len(std), 16)
        self.assertEqual(std[:12], snap[:12])
        self.assertEqual(struct.unpack_from('<I', std, 12)[0], CT[0])
        self.assertEqual(struct.unpack_from('<I', snap, 12)[0], ALIGN)

    @unittest.skipUnless(HAVE, 'extracted/ missing')
    def test_1st_read_gets_the_cave_and_only_zero_bytes_change(self):
        k = FP.read_extracted('1ST_READ.BIN')
        out, rep, ctl = built()
        new = out['/1ST_READ.BIN']
        self.assertEqual(len(new), len(k))
        diff = [i for i in range(len(k)) if new[i] != k[i]]
        lo, hi = ALIGN - FP.IMG_BASE, 0x8C299A00 - FP.IMG_BASE
        self.assertTrue(diff and min(diff) >= lo and max(diff) < hi)
        ab = FP.align_bytes(ALIGN, CT[1])
        self.assertEqual(new[ALIGN - FP.IMG_BASE:ALIGN - FP.IMG_BASE + len(ab)], ab)
        # without the option the 1ST_READ differs from the align build exactly in the align cave (the font cave is not touched any more)
        c = ctl['/1ST_READ.BIN']
        d2 = [i for i in range(len(k)) if new[i] != c[i]]
        self.assertTrue(d2 and all(lo <= i < lo + 0x100 for i in d2))
        self.assertEqual(new[CT[0] - FP.IMG_BASE:CT[0] - FP.IMG_BASE + FP.CAVE_SIZE], c[CT[0] - FP.IMG_BASE:CT[0] - FP.IMG_BASE + FP.CAVE_SIZE])
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(k, table(), PE.REGISTRY and FP.PLACEMENTS['gap1'], align=True)       # gap1 has no align cave
        with self.assertRaises(FP.FontPatchError):
            FP.make_patches(FP.read_extracted, paths=[], align_fix=True, variants='ABC')


# ------------------------------------------------------------------------------------------------ the blank-run snap
@unittest.skipUnless(HAVE, 'extracted/ missing')
class ShirtNumberColumn(unittest.TestCase):
    """PLNUMSET builds each row as name + blanks up to byte 14 + the %2d number (docs/layout-issues.md s10.2)"""
    NAMES = ['Ito', 'Kenji', 'Takahashi', 'Nakagawa', 'Isao Nakagak', 'Wanyama Wang', 'Li', 'Okamoto']

    def row(self, name, num):
        s = (name + ' ' * 14)[:14] if len(name) <= 12 else name
        return s + ('%2d' % num)

    def digit_x(self, snaps, s, idx):
        # pen after code idx-1 = where code idx is drawn (x0 for idx 0)
        return snaps[idx - 1][0]

    def run_rows(self, align):
        out, rep, ctl = built()
        img = (out if align else ctl)['/FLOW_PRG/PLNUMSET.BIN']
        _, h1 = h1_of('FLOW_PRG/PLNUMSET.BIN')
        ex, nat = caves(table(), align)
        xs = {}
        for nm in self.NAMES:
            s = self.row(nm, 7)
            snaps = run_layout(img, h1, codes_of(s), W=20, A=24, flag=1, x0=100, extra=ex, native=nat)
            xs[nm] = self.digit_x(snaps, s, 15)           # the '7' is byte 15 (the %2d pad blank is byte 14)
        return xs

    def test_all_numbers_land_on_the_original_pixel(self):
        xs = self.run_rows(True)
        self.assertEqual(set(xs.values()), {100 + 12 * 15}, xs)

    def test_control_without_the_fix_is_ragged(self):
        xs = self.run_rows(False)
        self.assertGreater(len(set(xs.values())), 3, xs)           # 'all over the place'

    def test_two_digit_numbers_start_at_byte_14(self):
        out, rep, ctl = built()
        _, h1 = h1_of('FLOW_PRG/PLNUMSET.BIN')
        ex, nat = caves(table(), True)
        for nm in ('Ito', 'Takahashi', 'Isao Nakagak', 'Nakagawa'):
            s = self.row(nm, 23)
            snaps = run_layout(out['/FLOW_PRG/PLNUMSET.BIN'], h1, codes_of(s), x0=100, extra=ex, native=nat)
            self.assertEqual(snaps[14 - 1][0], 100 + 12 * 14, nm)          # pen before byte 14 (the '2'): the same pixel for every name
            self.assertEqual(snaps[15 - 1][0], 100 + 12 * 15, nm)          # and the digits keep their 12 px pitch

    def test_word_spaces_and_text_without_runs_are_unchanged(self):
        out, rep, ctl = built_all()
        _, h1 = h1_of('FLOW_PRG/MEETING.BIN')
        ex, nat = caves(table(), True)
        ex0, nat0 = caves(table(), False)
        for s in ('The goalkeeper is injured.', 'Hello, World! iiii WWWW', 'a b c d', '  leading'[2:], 'no runs here at all'):
            a = run_layout(out['/FLOW_PRG/MEETING.BIN'], h1, codes_of(s), extra=ex, native=nat)
            b = run_layout(ctl['/FLOW_PRG/MEETING.BIN'], h1, codes_of(s), extra=ex0, native=nat0)
            self.assertEqual(a, b, s)

    def test_blank_run_edge_cases(self):
        out, rep, ctl = built_all()
        _, h1 = h1_of('FLOW_PRG/MEETING.BIN')
        img = out['/FLOW_PRG/MEETING.BIN']
        ex, nat = caves(table(), True)
        t = table()
        # a leading run (right aligned number): the digit sits at x0 + 12 * 3
        sn = run_layout(img, h1, codes_of('   7'), extra=ex, native=nat)
        self.assertEqual(sn[2][0], 20 + 12 * 3)
        # a trailing run and a run before a newline do nothing special
        a = run_layout(img, h1, codes_of('ab   ') + [0x200A] + codes_of('cd'), extra=ex, native=nat)
        self.assertEqual(a[-1], (20 + t[ord('c')] + t[ord('d')], 240 + 24))
        self.assertEqual([x[0] for x in a[:5]], [x[0] for x in run_layout(ctl['/FLOW_PRG/MEETING.BIN'], h1, codes_of('ab   ') + [0x200A] + codes_of('cd'),
                                                                            extra=caves(t, False)[0], native=caves(t, False)[1])[:5]])
        # a run followed by a colour control and then a glyph still lands on the grid
        c = run_layout(img, h1, codes_of('ab  ') + [0x2012] + codes_of('X'), extra=ex, native=nat)
        self.assertEqual(c[3][0], 20 + 12 * 4)
        # the pad blanks shrink (4 px at least) to absorb a proportional overshoot: ten 13 px letters, then two blanks
        sn = run_layout(img, h1, codes_of('WWWWWWWWWW  7'), extra=ex, native=nat)
        self.assertEqual(sn[11][0], 20 + 12 * 12)
        self.assertEqual(sn[10][0] - sn[9][0], 4)                       # the first pad blank shrank
        # twelve 13 px letters and two blanks and a pad: still on the grid
        sn = run_layout(img, h1, codes_of('WWWWWWWWWWWW   7'), extra=ex, native=nat)
        self.assertEqual(sn[14][0], 20 + 12 * 15)
        # full-width glyphs count two cells
        sn = run_layout(img, h1, [0x0123, 0x0124] + codes_of('  5'), extra=ex, native=nat)
        self.assertEqual(sn[3][0], 20 + 12 * 6)
        # a second line after a newline restarts the grid (units = 0, x0)
        sn = run_layout(img, h1, codes_of('abc') + [0x200A] + codes_of('xy  Z'), extra=ex, native=nat)
        self.assertEqual(sn[7][0], 20 + 12 * 4)


@unittest.skipUnless(HAVE, 'extracted/ missing')
class ControlIsIdentity(unittest.TestCase):
    """with the all-12 'control' table the align fix must change nothing: blank runs reach the grid they are already on, pw3 gives 4 * len"""

    def test_layout_with_all12_table_equals_the_original_code(self):
        d, h1 = h1_of('FLOW_PRG/PLNUMSET.BIN')
        all12 = bytes([12]) * 256
        # the original image (no hooks at all) versus the hooked image with the align cave and an all-12 table
        out, rep = FP.make_patches(FP.read_extracted, paths=['FLOW_PRG/PLNUMSET.BIN'], align_fix='default', glyphs=False)
        img = out['/FLOW_PRG/PLNUMSET.BIN']
        ex, nat = caves(all12, True)
        for s in ('Ito          12', 'Takahashi     7', '   7', 'a  b   c', 'Hello, World!  iiii  WWWW', 'x' * 30 + '  y',
                  'name  ' + ' ' * 3 + '12', 'The goalkeeper is injured.'):
            for W, flag in ((20, 1), (9, 0), (13, 1)):
                a = run_layout(img, h1, codes_of(s), W=W, flag=flag, extra=ex, native=nat)
                b = run_layout(d, h1, codes_of(s), W=W, flag=flag)
                self.assertEqual(a, b, (s, W, flag))

    def test_pw3_with_all12_table_is_four_per_byte(self):
        all12 = bytes([12]) * 256
        for s in (b'Tokyo', b'Season', b'Age 25', b'', b'x' * 17, '東京都'.encode('cp932')):
            self.assertEqual(run_pw3(all12, s), 4 * len(s) if s else 0)


@unittest.skipUnless(HAVE, 'extracted/ missing')
class EveryOverlay(unittest.TestCase):
    """the frame slot / window offsets the snap reads are those of variant A in every one of the 98 hooked overlays
    (a sample by default, all with ALIGN_FULL=1)"""

    def test_snap_in_hooked_overlays(self):
        import random
        out, rep = FP.make_patches(FP.read_extracted, align_fix='snap-all')
        files = [r for r, v in rep['files']]
        self.assertEqual(len(files), 98)
        self.assertEqual([x[0] for x in rep['panel']], PANELS)
        self.assertEqual([x[1:] for x in rep['panel']], [(18, 8)] * 3)
        pick = files if os.environ.get('ALIGN_FULL') else random.Random(11).sample(files, 6)
        t = rep['table']
        ex, nat = caves(t, True)
        for rel in pick:
            _, h1 = h1_of(rel)
            sn = run_layout(out['/' + rel], h1, codes_of('Name  ' + ' ' * 3 + '12'), x0=40, extra=ex, native=nat)
            self.assertEqual(sn[10 - 1][0], 40 + 12 * 10, rel)           # 'Name' + 5 blanks, the '1' is code 9; pen before '1' = 40 + 12 * 9
            self.assertEqual(sn[9 - 1][0], 40 + 12 * 9, rel)


# ------------------------------------------------------------------------------------------------ pw3
def pw3_model(tbl, data):
    """Python reference of pw3: ceil(width / 3) of a NUL terminated cp932 byte string"""
    p, i = 0, 0
    while i < len(data) and data[i]:
        b = data[i]
        if b < 0x80:
            if b >= 0x20:
                p += (tbl[0] if b == 0x20 else tbl[b]) or 12
        elif 0xA0 <= b < 0xE0:
            p += tbl[b] or 12
        else:
            p += 24
            if i + 1 < len(data) and data[i + 1]:
                i += 1
        i += 1
    return (p + 2) // 3, p


def run_pw3(tbl, data):
    m = sh4sim.Machine()
    code, sym = FP.align_assembly(ALIGN, CT[1])
    m.load(ALIGN, code)
    m.load(CT[1], tbl)
    buf = 0x8D000000 - 0x1000
    for i, b in enumerate(data + b'\0\0'):
        m.wn(buf + i, b, 1)
    m.R[4] = buf
    m.R[1] = 0x11111111
    m.R[2] = 0x22222222
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    m.native = [(ALIGN, ALIGN + 0x100)]
    m.run(sym['pw3'], 0x8C000000, max_steps=20000)
    assert m.R[1] == 0x11111111 and m.R[2] == 0x22222222 and m.R[15] == 0x8D000000 - 0x100
    return sh4sim.s32(m.R[0])


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Pw3(unittest.TestCase):
    def test_against_reference(self):
        import random
        t = table()
        rnd = random.Random(3)
        items = [b'', b'A', b' ', b'Tokyo', b'Season', b'Average', b'Age 25', b'1/2 yrs', b'3100 man', b'0 apps', b'0 goals', b'0.00 pts',
                 'Isao Nakagawa'.encode(), '東京都'.encode('cp932'), '本年成績'.encode('cp932'), b'\xb1\xb2\xb3', b'ab\x81', b'\x0aab', b'\xe0\x80xyz']
        for _ in range(120):
            n = rnd.randint(0, 20)
            items.append(bytes(rnd.choice([rnd.randint(1, 255), rnd.randint(0x20, 0x7E), rnd.randint(0x20, 0x7E)]) for _ in range(n)))
        for it in items:
            want, p = pw3_model(t, it)
            self.assertEqual(run_pw3(t, it), want, it)

    def test_japanese_equals_the_old_cell_count(self):
        t = table()
        for s in ('東京都', '本年成績', '平均評価', '神奈川県'):
            b = s.encode('cp932')
            self.assertEqual(run_pw3(t, b) * 3, len(b) * 12)              # 24 px per two byte glyph: exactly the old 12 * strlen

    def test_ceil_division_is_exact(self):
        for x in range(0, 4000):
            self.assertEqual(((x + 2) * 21846) >> 16, (x + 2) // 3)


# ------------------------------------------------------------------------------------------------ the player-card panel
@unittest.skipUnless(HAVE, 'extracted/ missing')
class Panel(unittest.TestCase):
    def test_scan_counts_and_equal_layout(self):
        for rel in PANELS:
            d = FP.read_extracted(rel)
            shl, pools = FP.panel_scan(d, rel)
            self.assertEqual((len(shl), len(pools)), (20, 8), rel)
            sal = FP.salary_sites(d, rel)
            self.assertEqual(len(sal), 2, rel)
            self.assertTrue(set(sal) <= set(shl), rel)
            for o in shl:
                w = struct.unpack_from('<H', d, o)[0]
                self.assertEqual(w & 0xF0FF, 0x4008, (rel, hex(o)))              # shll2 rN
            for p in pools:
                self.assertEqual(struct.unpack_from('<I', d, p)[0], FP.STRLEN_ADDR)

    def test_patched_bytes(self):
        out, rep, ctl = built()
        self.assertEqual([x[0] for x in rep['panel']], PANELS)
        for rel in PANELS:
            d = FP.read_extracted(rel)
            nd = out['/' + rel]
            shl, pools = FP.panel_scan(d, rel)
            sal = FP.salary_sites(d, rel)
            self.assertEqual(len([o for o in shl if o not in sal]), 18, rel)
            for o in shl:
                if o in sal:
                    self.assertEqual(nd[o:o + 2], bytes.fromhex('0842'), (rel, hex(o)))       # the salary idiom keeps its shll2
                else:
                    self.assertEqual(nd[o:o + 2], FP.NOP)
            for p in pools:
                self.assertEqual(struct.unpack_from('<I', nd, p)[0], rep['pw3'])
            # everything else is the font hooks (the control build has them too): the align build differs from the control only in the panel edits
            c = ctl['/' + rel]
            diff = [i for i in range(len(d)) if nd[i] != c[i]]
            allowed = set()
            for o in shl:
                if o not in sal:
                    allowed.update((o, o + 1))
            for p in pools:
                allowed.update(range(p, p + 4))
            self.assertTrue(set(diff) <= allowed and diff, rel)
            for o in sal:
                self.assertFalse({o, o + 1} & set(diff), (rel, hex(o)))
            self.assertEqual(len(nd), len(d))

    def test_refuses_patched_and_foreign_images(self):
        out, rep, ctl = built()
        with self.assertRaises(FP.FontPatchError):
            FP.panel_scan(out['/' + PANELS[0]], PANELS[0])                       # already patched
        with self.assertRaises(FP.FontPatchError):
            FP.panel_scan(FP.read_extracted('FLOW_PRG/MEETING.BIN'), 'MEETING')    # not a panel overlay
        d = bytearray(FP.read_extracted(PANELS[0]))
        shl, pools = FP.panel_scan(bytes(d), PANELS[0])
        struct.pack_into('<I', d, pools[0], 0x8C014DE8)                          # a changed pool literal
        with self.assertRaises(FP.FontPatchError):
            FP.panel_scan(bytes(d), PANELS[0])

    def test_idiom_arithmetic_from_the_patched_bytes(self):
        """execute `mov rL,rT ... sub rL,rT` of every patched site: x = anchor - 3 * len3 (the original gave anchor - 12 * len)"""
        out, rep, ctl = built()
        n = 0
        for rel in PANELS:
            d = FP.read_extracted(rel)
            nd = out['/' + rel]
            shl, pools = FP.panel_scan(d, rel)
            sal = FP.salary_sites(d, rel)
            ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
            for o in shl:
                i = o // 2
                # idiom start: the `mov rT,rL` hit before the shll2 (within 8 words), end: the `sub rL,rT`
                st = [j for j in range(i - 8, i) if ws[j] >> 12 == 6 and (ws[j] & 15) == 3 and ws[j + 1] == 0x4000 | ((ws[j] >> 4) & 15) << 8][-1]
                en = [j for j in range(i + 1, i + 6) if ws[j] & 0xF00F == 0x3008][0]
                Lr, Tr = (ws[st] >> 4) & 15, (ws[st] >> 8) & 15
                for src, label in ((d, 'orig'), (nd, 'patched')):
                    for length in (1, 5, 8, 22, 31):
                        m = sh4sim.Machine()
                        m.load(BASE, src)
                        m.R[Lr] = length
                        m.R[12] = 600
                        m.R[15] = 0x8D000000 - 0x100
                        m.native = [(BASE, BASE + len(src))]
                        m.run(BASE + st * 2, BASE + (en + 1) * 2, max_steps=100)
                        x = sh4sim.s32(m.R[ws[en] >> 8 & 15])
                        self.assertEqual(x, 600 - (12 if label == 'orig' or o in sal else 3) * length, (rel, hex(o), label, length))
                        n += 1
        self.assertEqual(n, 3 * 20 * 2 * 5)

    def test_real_text_ends_at_the_anchor(self):
        """lay out the real strings with the patched layout function at x0 = anchor - 3 * len3: the text ends within 2 px of the anchor,
        where the original (12 * strlen) placement overflowed it"""
        out, rep, ctl = built()
        t = table()
        anchor = 612
        rel = PANELS[0]
        _, h1 = h1_of(rel)
        ex, nat = caves(t, True)
        over_before = []
        for s in ('Tokyo', 'Season', 'Average', 'Age 25', '1/2 yrs', '3100 man', 'DF', '0 apps', '0 goals', '0.00 pts', 'Isao Nakagawa', 'Hokkaido',
                  'Kanagawa', '12 oku 3400 man', 'Yamanashi', 'GK', '2 yrs'):
            len3 = run_pw3(t, s.encode())
            x0 = anchor - 3 * len3
            snaps = run_layout(out['/' + rel], h1, codes_of(s), x0=x0, extra=ex, native=nat)
            end = snaps[-1][0]
            self.assertLessEqual(end, anchor, s)
            self.assertGreaterEqual(end, anchor - 2, s)
            old_end = anchor - 12 * len(s) + pen_of(t, s)
            if old_end > anchor:
                over_before.append((s, old_end - anchor))
        self.assertGreaterEqual(len(over_before), 4, over_before)            # the defect existed: Tokyo, Season, ... overflowed


# ------------------------------------------------------------------------------------------------ the salary cell
def _salary_cell(rel, nd, v, nop_it=False):
    """the REAL salary setter of the patched overlay `nd` (CAP_SLCT 0x9510, same code in ENDOPT / EVENT) with the REAL money cave hooked
    into the overlay's money function, then the REAL idiom bytes: returns (count the setter returned, text, x of the cell, end of the text)"""
    import moneycheck as MC
    import moneypatch as MP
    d = FP.read_extracted(rel)
    sal = FP.salary_sites(d, rel)
    delta = sal[0] - 0xA03A                                         # the code is identical in the three overlays (CAP_SLCT = 0)
    money_lit = struct.unpack_from('<I', d, 0x961C + delta)[0]
    wtext_lit = struct.unpack_from('<I', d, 0x9604 + delta)[0]
    moff = MP.find_sites(d, rel)[0]['off']
    base = money_lit - moff
    img = bytearray(nd)
    if nop_it:
        for o in sal:
            img[o:o + 2] = FP.NOP                                   # the defect of stage 8b: salary idiom nopped like the others
    cave = MP.cave_bytes()
    m = MC.Mach()
    m.load(base, bytes(img))
    m.load(base + moff, MP.hook_bytes())                            # what moneypatch writes into the overlay
    m.load(MP.CAVE_ADDR, cave)
    m.native = [(base, base + len(img)), (MP.CAVE_ADDR, MP.CAVE_ADDR + len(cave))]
    seen = []

    def wtext(mm):                                                  # the window text setter: remember the string (top of the stack = buffer)
        a = mm.rn(mm.R[15], 4)
        s = bytearray()
        while mm.rb(a + len(s)):
            s.append(mm.rb(a + len(s)))
        seen.append(bytes(s))
    m.ext_ret[wtext_lit] = wtext
    m.R[4] = 0x8D000000 - 0x8000
    m.R[5] = v
    m.R[15] = 0x8D000000 - 0x100
    m.PR = 0x8C000000
    m.run(base + 0x9510 + delta, 0x8C000000, max_steps=200000)
    count = m.R[0]
    # the idiom: `mov r2,r1 ... sub r2,r1` (anchor r12, count r2 = the half word the constructor stored at card + 104)
    m2 = sh4sim.Machine()
    m2.load(base, bytes(img))
    m2.R[2] = count
    m2.R[12] = 600
    m2.native = [(base, base + len(img))]
    m2.run(base + sal[0] - 8, base + sal[0] + 4, max_steps=100)
    x = sh4sim.s32(m2.R[1])
    return count, seen[-1], x, x + pen_of(table(), seen[-1].decode())


@unittest.skipUnless(HAVE, 'extracted/ missing')
class Salary(unittest.TestCase):
    """the salary cell (card + 104) is placed with a CHARACTER count (the money function's return), not a pw3: its `shll2` must stay"""

    def test_setter_returns_the_character_count(self):
        out, rep, ctl = built()
        for rel in PANELS:
            for v in (1, 800, 1400, 3100, 7800, 9999):
                count, text, x, end = _salary_cell(rel, out['/' + rel], v)
                self.assertEqual(count, len(text), (rel, v, text))                   # 1 byte = 1 character: `1400 man` -> 8

    def test_right_edge_is_at_the_anchor(self):
        out, rep, ctl = built()
        for rel in PANELS:
            for v in (1, 800, 1400, 3100, 7800, 9999):
                count, text, x, end = _salary_cell(rel, out['/' + rel], v)
                self.assertEqual(x, 600 - 12 * count, (rel, v))
                self.assertLessEqual(abs(end - 600), 3, (rel, v, text, end))

    def test_nopping_the_salary_idiom_was_the_defect(self):
        """control: with the salary `shll2` nopped (stage 8b) the text of `1400 man` ends 72 px right of the anchor"""
        out, rep, ctl = built()
        for rel in PANELS:
            count, text, x, end = _salary_cell(rel, out['/' + rel], 1400, nop_it=True)
            self.assertEqual(text, b'1400 man')
            self.assertEqual(x, 600 - 3 * 8)
            self.assertGreaterEqual(end - 600, 70, rel)

    def test_signature_is_found_twice_and_refused_otherwise(self):
        for rel in PANELS:
            d = FP.read_extracted(rel)
            self.assertEqual(len(FP.salary_sites(d, rel)), 2)
        d = bytearray(FP.read_extracted(PANELS[0]))
        for o in FP.salary_sites(bytes(d), 'x'):
            d[o:o + 2] = FP.NOP
        with self.assertRaises(FP.FontPatchError):
            FP.salary_sites(bytes(d), 'patched')
        with self.assertRaises(FP.FontPatchError):
            FP.salary_sites(FP.read_extracted('FLOW_PRG/MEETING.BIN'), 'MEETING')


if __name__ == '__main__':
    unittest.main(verbosity=1)
