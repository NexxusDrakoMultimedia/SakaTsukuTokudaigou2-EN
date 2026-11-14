"""Isolation tests of the alignment fix (stage 8h, docs/layout-issues.md section 10.9).  Nothing starts an emulator.

    python -I -X utf8 tools/test_align_isolation.py

Background: with the stage 8b wiring (`bra at_snap` in the font cave, so EVERY proportional draw of every overlay passed through the snap, and 20 nops
+ 8 pw3 literals in EVENT / CAP_SLCT / ENDOPT) a playtest hung at the first message after the manager was picked.  The cause was not found in any
simulation (section 10.9), so the fix is now isolated by construction:

* the font cave is byte-identical with and without --align-fix; only the overlays in ALIGN_SNAP_FILES (PLNUMSET) get a hook literal that points at
  the align cave; every other overlay is byte-identical to the align-off build (except the three panel overlays, which differ only in the panel edits);
* `at_snap` hands every glyph other than a blank in a window with A == 24 to the unchanged font cave, validates its frame assumption (index < count
  and codes[index] is the blank being laid out) and looks ahead at most 63 codes, so a frame that is not the proven one gets the plain table advance;
* the real layout function of real overlays, laid out through the cave with the snap in EVERY overlay (mode 'snap-all', the worst case) and without
  it, gives identical pen positions for every string without a blank run (the message window typewriter of SCDRF / EVENT, panels, menus, DRAFT, HOMETOWN ...).
"""
import json
import os
import re
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontcheck as FC       # noqa: E402
import fontpatch as FP       # noqa: E402
import sh4sim                # noqa: E402

HAVE = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'))
ROOT = os.path.dirname(HERE)
CT = FP.placement()
ALIGN = FP.align_address()
BASE = 0x8C2D0000
K_BASE = FP.IMG_BASE

_cache = {}


def full(mode):
    """make_patches over all overlays (about 1 s) for an align mode (False = align off)"""
    if mode not in _cache:
        _cache[mode] = FP.make_patches(FP.read_extracted, align_fix=mode)
    return _cache[mode]


def diff_bytes(a, b):
    return [i for i in range(len(a)) if a[i] != b[i]]


# ------------------------------------------------------------------------------------------------ 1. byte level isolation
@unittest.skipUnless(HAVE, 'extracted/ missing')
class ByteIsolation(unittest.TestCase):
    def test_default_mode_changes_only_what_it_must(self):
        off, _ = full(False)
        on, rep = full('default')
        self.assertEqual(rep['align_mode'], 'default')
        self.assertEqual(rep['snap'], list(FP.ALIGN_SNAP_FILES))
        self.assertEqual(sorted(k for k in on if on[k] != off.get(k)),
                         sorted(['/1ST_READ.BIN', '/FLOW_PRG/PLNUMSET.BIN'] + ['/' + r for r in FP.ALIGN_FILES]))
        # every other file, i.e. 93 overlays, the fonts and the rest, is byte-identical to the align-off build
        self.assertEqual(len([k for k in on if on[k] == off.get(k)]), len(on) - 5)

    def test_font_cave_and_table_identical_in_1st_read(self):
        off, _ = full(False)
        on, _ = full('default')
        a, b = off['/1ST_READ.BIN'], on['/1ST_READ.BIN']
        d = diff_bytes(a, b)
        lo = ALIGN - K_BASE
        self.assertTrue(d and all(lo <= i < lo + 0x100 for i in d), 'only the align cave area may differ')
        self.assertEqual(a[CT[0] - K_BASE:CT[0] - K_BASE + 0x100], b[CT[0] - K_BASE:CT[0] - K_BASE + 0x100])      # the font cave (incl. its `rts`)
        self.assertEqual(a[CT[1] - K_BASE:CT[1] - K_BASE + 0x100], b[CT[1] - K_BASE:CT[1] - K_BASE + 0x100])

    def test_snap_overlay_differs_in_one_literal(self):
        off, _ = full(False)
        on, _ = full('default')
        rel = '/FLOW_PRG/PLNUMSET.BIN'
        d = diff_bytes(off[rel], on[rel])
        self.assertEqual(len(d), 1)                                    # the literal 0x8c299800 -> 0x8c299700: one byte (0x98 -> 0x97)
        site = FP.find_sites(FP.read_extracted('FLOW_PRG/PLNUMSET.BIN'), 'PLNUMSET')[0]['h1']
        self.assertTrue(all(site + 12 <= i < site + 16 for i in d))
        self.assertEqual(struct.unpack_from('<I', on[rel], site + 12)[0], ALIGN)
        self.assertEqual(struct.unpack_from('<I', off[rel], site + 12)[0], CT[0])

    def test_panel_overlays_differ_only_in_the_panel_edits(self):
        off, _ = full(False)
        on, _ = full('default')
        for rel in FP.ALIGN_FILES:
            d0 = FP.read_extracted(rel)
            shl, pools = FP.panel_scan(d0, rel)
            sal = FP.salary_sites(d0, rel)
            allowed = set()
            for o in shl:
                if o not in sal:                                  # the 2 salary idioms keep their shll2 (character count, not pw3)
                    allowed.update((o, o + 1))
            for p in pools:
                allowed.update(range(p, p + 4))
            d = diff_bytes(off['/' + rel], on['/' + rel])
            self.assertTrue(d and set(d) <= allowed, rel)
            self.assertEqual(sum(1 for o in shl if o not in sal and {o, o + 1} <= set(d)), 18, rel)       # 18 nops per overlay, not 20
            for o in sal:
                self.assertEqual(on['/' + rel][o:o + 2], bytes.fromhex('0842'), (rel, hex(o)))

    def test_modes(self):
        off, _ = full(False)
        snap_only, r1 = full('snap-only')
        panel_only, r2 = full('panel-only')
        snap_all, r3 = full('snap-all')
        self.assertEqual(sorted(k for k in snap_only if snap_only[k] != off.get(k)), ['/1ST_READ.BIN', '/FLOW_PRG/PLNUMSET.BIN'])
        self.assertEqual(r1['panel'], [])
        self.assertEqual(sorted(k for k in panel_only if panel_only[k] != off.get(k)), sorted(['/1ST_READ.BIN'] + ['/' + r for r in FP.ALIGN_FILES]))
        self.assertEqual(r2['snap'], [])
        self.assertEqual(len(r3['snap']), 98)                         # the stage 8b wiring: every hooked overlay
        with self.assertRaises(FP.FontPatchError):
            FP.align_mode('everywhere')

    def test_env_switch(self):
        old = os.environ.get(FP.ALIGN_MODE_ENV)
        try:
            os.environ[FP.ALIGN_MODE_ENV] = 'panel-only'
            self.assertEqual(FP.align_mode(True), 'panel-only')
            self.assertEqual(FP.align_mode('snap-only'), 'snap-only')       # an explicit mode wins
            del os.environ[FP.ALIGN_MODE_ENV]
            self.assertEqual(FP.align_mode(True), 'default')
            os.environ[FP.ALIGN_MODE_ENV] = 'bogus'
            with self.assertRaises(FP.FontPatchError):
                FP.align_mode(True)
        finally:
            if old is None:
                os.environ.pop(FP.ALIGN_MODE_ENV, None)
            else:
                os.environ[FP.ALIGN_MODE_ENV] = old

    def test_cave_fits_and_does_not_reach_the_font_cave(self):
        code, sym = FP.align_assembly(ALIGN, CT[1], CT[0])
        self.assertLessEqual(len(code), FP.ALIGN_RESERVE)
        self.assertLessEqual(ALIGN + len(code), CT[0])


# ------------------------------------------------------------------------------------------------ 2. at_snap called directly
WIN = 0x8D000000 - 0x4000
ARR = WIN + 0x800
STACK = 0x8D000000 - 0x100


def call(entry, codes, idx, code=0x8000, A=24, pen=100, units=2, x0=40, n22=None, table=None, frame_i=None, before=()):
    """enter `entry` (at_snap or the font cave) the way the hook does: r4 = code, r14 = window, r10 = pen, r11 = units, @(4,r15) = index"""
    m = sh4sim.Machine()
    tbl = table or bytes([12]) * 256
    m.load(CT[0], FP.cave_bytes(CT))
    m.load(CT[1], tbl)
    m.load(ALIGN, FP.align_bytes(ALIGN, CT[1]))
    for i, c in enumerate(codes):
        m.wn(ARR + 2 * i, c, 2)
    for i, c in enumerate(before):             # words in FRONT of the code array (a wrapped index reaches them)
        m.wn(ARR - 2 * (len(before) - i), c, 2)
    m.wn(WIN + 0x30, ARR, 4)
    m.wn(WIN + 0x22, len(codes) if n22 is None else n22, 2)
    m.wn(WIN + 0x3E, A & 0xFF, 1)
    m.wn(WIN + 0x4A, x0, 2)
    m.R[4] = code
    m.R[14] = WIN
    m.R[10] = pen
    m.R[11] = units
    for r in (6, 7, 8, 9, 12, 13):
        m.R[r] = 0x1000 + r
    m.R[15] = STACK
    m.wn(STACK + 4, idx if frame_i is None else frame_i, 4)
    m.PR = 0x8C000000
    m.native = [(CT[0], CT[0] + 0x100), (ALIGN, ALIGN + 0x100)]
    m.run(entry, 0x8C000000, max_steps=20000)
    return m


def blanks(n):
    return [0x2020] * n


G = lambda ch: 0x8000 | ord(ch)       # noqa: E731


class AtSnapDirect(unittest.TestCase):
    def table(self):
        t = bytearray([12]) * 256
        for c in 'WMm':
            t[ord(c)] = 13
        for c in 'il.,':
            t[ord(c)] = 5
        return bytes(t)

    def same_as_cave(self, codes, idx, **kw):
        a = call(ALIGN, codes, idx, **kw)
        b = call(CT[0], codes, idx, **kw)
        self.assertEqual(sh4sim.s32(a.R[0]), sh4sim.s32(b.R[0]), (codes, idx, kw))
        for r in (4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15):
            self.assertEqual(a.R[r], b.R[r], (r, codes, idx, kw))
        return sh4sim.s32(a.R[0])

    def test_every_glyph_but_the_blank_is_the_unchanged_routine(self):
        t = self.table()
        for ch in 'aiWM.,0189~!':
            for A in (24, 16, 32, 10):
                self.same_as_cave([G('a'), G(ch), G('b')], 1, code=G(ch), A=A, table=t)

    def test_blank_in_other_windows_is_the_unchanged_routine(self):
        for A in (16, 32, 10, 12, 48):
            for codes, idx in (([G('a')] + blanks(4) + [G('b')], 1), ([G('a')] + blanks(4) + [G('b')], 2), (blanks(3), 0)):
                self.same_as_cave(codes, idx, A=A)

    def test_single_blank_and_trailing_blanks_are_the_table_advance(self):
        t = self.table()
        self.assertEqual(self.same_as_cave([G('a'), 0x2020, G('b')], 1, table=t), 12)
        self.assertEqual(self.same_as_cave([G('a'), 0x2020, 0x200A, G('b')], 1, table=t), 12)
        self.assertEqual(self.same_as_cave([G('a'), 0x2020, 0x2020], 1, table=t), 12)                 # run to the end of the text
        self.assertEqual(self.same_as_cave([G('a'), 0x2020, 0x2020, 0x200A, G('b')], 1, table=t), 12)  # run before a newline

    def test_proven_frame_snaps_to_the_grid(self):
        # 'ab', then a run of 3 blanks, then 'c': pen 100 after 'ab' (x0 40 + 2 units of 12 would be 64: the text is wider), blank index 2, units 2
        codes = [G('a'), G('b')] + blanks(3) + [G('c')]
        m = call(ALIGN, codes, 4, pen=70, units=4, x0=40)                 # the LAST blank of the run (index 4): grid after it = 40 + 12 * 5 = 100
        self.assertEqual(sh4sim.s32(m.R[0]), 100 - 70)
        m = call(ALIGN, codes, 2, pen=70, units=2, x0=40)                 # the first blank of the run
        self.assertEqual(sh4sim.s32(m.R[0]), 40 + 12 * 3 - 70 if 40 + 12 * 3 - 70 > 4 else 4)
        m = call(ALIGN, codes, 4, pen=200, units=4, x0=40)                # overshoot: a pad blank shrinks to 4 px
        self.assertEqual(sh4sim.s32(m.R[0]), 4)

    def test_wrong_frame_gets_the_plain_table_advance(self):
        codes = [G('a'), G('b')] + blanks(3) + [G('c')]
        for bad in (0x7FFFFFFF, 0xFFFFFFF0, 1000, 6, 7, 0, 1, 5):         # not the index of a blank / beyond the text / garbage
            m = call(ALIGN, codes, 0, frame_i=bad, pen=70, units=4)
            self.assertEqual(sh4sim.s32(m.R[0]), 12, bad)
        # the code count of the window too small (or zero): i >= n
        for n22 in (0, 1, 3):
            m = call(ALIGN, codes, 4, n22=n22, pen=70, units=4)
            self.assertEqual(sh4sim.s32(m.R[0]), 12, n22)
        # a huge or negative count: no exception, no endless scan (look-ahead is capped), same answer as the font cave or a snap of the run
        for n22 in (0x7FFF, 0xFFFF, 0x8000):
            m = call(ALIGN, codes, 4, n22=n22, pen=70, units=4)
            self.assertIn(sh4sim.s32(m.R[0]), (12, 30))

    def test_index_that_wraps_below_the_array_gets_the_plain_advance(self):
        # s8hk: 2 * 0x7fffffff wraps to -2, so &codes[i] is the word BEFORE the array; with a blank run standing there the stage 8h check
        # (i < n only) accepted it and snapped; the lower bound (&codes[i] >= array) sends it to the font cave
        codes = blanks(3) + [G('c')]
        for bad in (0x7FFFFFFF, 0xFFFFFFFF, 0xFFFFFFFE):
            m = call(ALIGN, codes, 0, frame_i=bad, pen=70, units=4, before=[0x2020, 0x2020, 0x2020])
            self.assertEqual(sh4sim.s32(m.R[0]), 12, hex(bad))

    def test_lookahead_is_capped(self):
        short = [G('a')] + blanks(10) + [G('b')]
        longr = [G('a')] + blanks(70) + [G('b')]
        m = call(ALIGN, short, 1, pen=60, units=1, x0=40)
        self.assertEqual(sh4sim.s32(m.R[0]), 4)                                                  # the grid pixel (40 + 12 * 2 = 64) is only 4 px ahead: 4 px
        m = call(ALIGN, short, 3, pen=45, units=3, x0=40)
        self.assertEqual(sh4sim.s32(m.R[0]), 40 + 12 * 4 - 45)
        m = call(ALIGN, longr, 5, pen=45, units=5, x0=40)                 # a run of 70 blanks is not a column: the plain advance
        self.assertEqual(sh4sim.s32(m.R[0]), 12)

    def test_registers_the_hook_does_not_save_are_never_read_after(self):
        # the layout needs r10 / r11 / r12 / r13 / r14 / r8 / r9 and the frame back: the cave must not change them or the stack
        codes = [G('a'), G('b')] + blanks(3) + [G('c')]
        m = call(ALIGN, codes, 4, pen=70, units=4)
        for r, v in ((6, 0x1006), (7, 0x1007), (8, 0x1008), (9, 0x1009), (12, 0x100C), (13, 0x100D), (10, 70), (11, 4), (14, WIN), (15, STACK)):
            self.assertEqual(m.R[r], v, r)
        self.assertEqual(m.rn(STACK + 4, 4), 4)


# ------------------------------------------------------------------------------------------------ 3. real overlays, real strings
class Lazy(dict):
    """byte memory backed by the (patched) 1ST_READ.BIN and one overlay image; writes go to the dict"""
    def __init__(self, k, ov):
        super().__init__()
        self.k, self.ov = k, ov

    def get(self, a, d=0):
        if a in self:
            return dict.__getitem__(self, a)
        o = a - BASE
        if 0 <= o < len(self.ov):
            return self.ov[o]
        o = a - K_BASE
        if 0 <= o < len(self.k):
            return self.k[o]
        return d


class Rig:
    """the real layout function of one overlay (patched by make_patches in a given mode) in the real 1ST_READ.BIN of the same build"""
    def __init__(self, rel, mode):
        out, rep = FP.make_patches(FP.read_extracted, paths=[rel], align_fix=mode)
        self.k = out['/1ST_READ.BIN']
        self.ov = out['/' + rel]
        d = FP.read_extracted(rel)
        h1 = FP.find_sites(d, rel)[0]['h1']
        fe = self.ov.rfind(FC.PROLOGUE, h1 - 0x500, h1)
        self.func, self.join = BASE + fe, BASE + h1 + 0x1A

    def pens(self, codes, W=20, cnt=None, A=24, flag=1, x0=20, y0=240):
        m = sh4sim.Machine()
        m.mem = Lazy(self.k, self.ov)
        win = 0x8D000000 - 0x4000
        arr = win + 0x800
        for i, c in enumerate(codes):
            m.wn(arr + 2 * i, c, 2)
        m.wn(win + 0x30, arr, 4)
        m.wn(win + 0x2C, len(codes) if cnt is None else cnt, 2)
        m.wn(win + 0x22, len(codes), 2)
        m.wn(win + 0x3C, W, 1)
        m.wn(win + 0x3E, A & 0xFF, 1)
        m.wn(win + 0x3F, 24, 1)
        m.wn(win + 0x45, flag, 1)
        m.wn(win + 0x4A, x0, 2)
        m.wn(win + 0x4C, y0, 2)
        m.wn(win + 56, 0x20, 4)
        m.R[4] = win
        m.R[15] = 0x8D000000 - 0x100
        m.PR = 0x8C000000
        m.native = [(BASE, BASE + len(self.ov)), (CT[0], CT[0] + 0x100), (ALIGN, ALIGN + 0x100)]
        pens = []
        m.run(self.func, 0x8C000000, watch={self.join: lambda mm: pens.append((sh4sim.s32(mm.R[10]), sh4sim.s32(mm.R[8])))}, max_steps=3000000)
        return pens


def codes_of(s):
    return [0x2020 if ch == ' ' else (0x200A if ch == '\n' else 0x8000 | ord(ch)) for ch in s]


def db_strings(rel, limit):
    """English strings of an overlay's database file with the printf / tag tokens replaced by samples; at most `limit`, spread over the file"""
    path = os.path.join(ROOT, 'translation', rel.replace('/', '__') + '.jsonl')
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding='utf-8') as fh:
        lines = fh.readlines()
    for line in lines:
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get('en') or ''
        s = re.sub(r'<[^>]+>', '', en)
        s = re.sub(r'=[a-z]/', '', s).replace('@Y/', '').replace('@P/', '').replace('@', '').replace('$1', 'Kenji').replace('$2', 'Hanako')
        s = s.replace('%2d', '12').replace('%d', '1234').replace('%s', 'Name').replace('%4d', '2026')
        if s and len(s) <= 160 and not re.search(r'[^\x20-\x7e\n]', s):
            rows.append(s)
    step = max(1, len(rows) // limit)
    return rows[::step][:limit]


BATTERY = [('FLOW_PRG/SCDRF.BIN', 14), ('FLOW_PRG/EVENT.BIN', 10), ('FLOW_PRG/SEARCH.BIN', 8), ('FLOW_PRG/GAME.BIN', 8), ('FLOW_PRG/DRAFT.BIN', 8),
           ('FLOW_PRG/HOMETOWN.BIN', 8), ('FLOW_PRG/MEETING.BIN', 8), ('FLOW_PRG/N_ENTRY.BIN', 6), ('FLOW_PRG/OPTION.BIN', 6)]


@unittest.skipUnless(HAVE, 'extracted/ missing')
class RealOverlays(unittest.TestCase):
    """the worst case: the snap in EVERY overlay ('snap-all', the stage 8b wiring) against the align-off build"""

    def test_message_window_and_screens_lay_out_identically(self):
        checked = changed_runs = 0
        for rel, limit in BATTERY:
            rig_on, rig_off = Rig(rel, 'snap-all'), Rig(rel, False)
            for s in db_strings(rel, limit):
                has_run = re.search(r'\S {2,}\S', s) is not None
                lines = [ln for ln in s.split('\n') if ln]
                runs = [(codes_of(s), 33, None)]                                  # a message window: three rows of the whole text
                runs.append((codes_of(lines[0]), 20, None))                       # a one line cell
                n = len(codes_of(s))
                runs.append((codes_of(s), 33, max(1, n // 2)))                     # a typewriter frame: half of the codes revealed
                for codes, W, cnt in runs:
                    a, b = rig_on.pens(codes, W, cnt), rig_off.pens(codes, W, cnt)
                    checked += 1
                    if a != b:
                        changed_runs += 1
                        self.assertTrue(has_run, '%s: layout changed for a string without a blank run: %r' % (rel, s))
        self.assertGreater(checked, 150)

    def test_scdrf_manager_greetings_with_the_typewriter(self):
        """the first message after the manager is picked (SCDRF, 'I can certainly build you a winning club.' ...): every typewriter frame, identical"""
        rig_on, rig_off = Rig('FLOW_PRG/SCDRF.BIN', 'snap-all'), Rig('FLOW_PRG/SCDRF.BIN', False)
        with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__SCDRF.BIN.jsonl'), encoding='utf-8') as fh:
            rows = [json.loads(l) for l in fh]
        greet = [r['en'] for r in rows if r.get('en') and r['en'].startswith(("I've always wanted", 'I can certainly', 'Just relax', 'Ah, you have'))]
        self.assertGreaterEqual(len(greet), 3)
        for s in greet:
            codes = codes_of(s)
            for cnt in range(1, len(codes) + 1, 5):
                self.assertEqual(rig_on.pens(codes, 33, cnt), rig_off.pens(codes, 33, cnt), (s, cnt))

    def test_blank_runs_still_differ_where_they_are_columns(self):
        rig_on, rig_off = Rig('FLOW_PRG/MEETING.BIN', 'snap-all'), Rig('FLOW_PRG/MEETING.BIN', False)
        s = 'Wanyama Wang   7'
        self.assertNotEqual(rig_on.pens(codes_of(s)), rig_off.pens(codes_of(s)))

    def test_default_mode_non_snap_overlay_equals_align_off(self):
        """in the default mode SCDRF / EVENT hooks are the align-off bytes, so every layout is trivially the same: prove it on the pens as well"""
        for rel in ('FLOW_PRG/SCDRF.BIN', 'FLOW_PRG/EVENT.BIN'):
            a, b = Rig(rel, 'default'), Rig(rel, False)
            for s in db_strings(rel, 6):
                self.assertEqual(a.pens(codes_of(s), 33), b.pens(codes_of(s), 33), (rel, s))


if __name__ == '__main__':
    unittest.main(verbosity=1)
