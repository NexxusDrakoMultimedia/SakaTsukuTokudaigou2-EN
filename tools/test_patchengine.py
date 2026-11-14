"""Tests of tools/patchengine.py (cave registry, overlap registry, masked-head families), of fontpatch / moneypatch on top of
it, and of the opt-in --prop-scale cave (executed in tools/sh4sim.py against a Python reference).
    python -I -X utf8 tools/test_patchengine.py"""
import hashlib
import os
import random
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpatch as FP  # noqa: E402
import moneypatch as MP  # noqa: E402
import patchengine as PE  # noqa: E402
import sh4asm2  # noqa: E402
import sh4sim  # noqa: E402

try:
    import capstone as _cs
    MD = _cs.Cs(_cs.CS_ARCH_SH, _cs.CS_MODE_SH4 | _cs.CS_MODE_LITTLE_ENDIAN)
except Exception:      # pragma: no cover
    MD = None

HAVE_EXTRACTED = os.path.exists(os.path.join(FP.EXTRACTED, '1ST_READ.BIN'))


# ------------------------------------------------------------------------------------------------ cave registry
class Registry(unittest.TestCase):
    def test_default_plan_is_collision_free_and_ordered(self):
        r = PE.default_registry()
        self.assertEqual(r.addr('font.cave'), 0x8C299800)
        self.assertEqual(r.addr('font.table'), 0x8C299900)
        self.assertEqual(r.addr('money.cave'), 0x8C299A00)
        self.assertEqual(r.addr('bank'), r['money.cave'].end)
        self.assertEqual(r['bank'].end, 0x8C2A0000)
        self.assertEqual((MP.CAVE_ADDR, MP.RESERVE), (0x8C299A00, 0x200))
        self.assertEqual(FP.PLACEMENTS['tail'], (0x8C299800, 0x8C299900))
        self.assertEqual(FP.PLACEMENTS['gap1'], (0x8C13BB80, 0x8C13BC00))
        tail = [c for c in r.table() if c.placement != 'gap1' and c.addr >= 0x8C299000]
        for a, b in zip(tail, tail[1:]):
            self.assertLessEqual(a.end, b.addr, (a, b))

    def test_collisions_are_refused(self):
        r = PE.default_registry()
        with self.assertRaises(PE.EngineError):
            r.claim('x', 0x8C299800, 0x40, 'money', 'tail')            # inside the font cave
        with self.assertRaises(PE.EngineError):
            r.claim('y', 0x8C299BF0, 0x20, 'other')                    # straddles money and bank
        with self.assertRaises(PE.EngineError):
            r.claim('font.cave', 0x8C2A0000, 0x10, 'font')              # duplicate name
        with self.assertRaises(PE.EngineError):
            r.claim('z', 0x8C299802, 0x10, 'other')                    # unaligned
        r.claim('ok', 0x8C13BC80, 0x80, 'font', 'other-placement')      # same owner, different placement tag may overlap alternatives
        with self.assertRaises(PE.EngineError):
            r.check_free(0x8C299900, 0x10, 'money')
        r.check_free(0x8C2A0000, 0x10, 'money')                         # beyond the plan

    def test_alloc(self):
        r = PE.default_registry()
        self.assertEqual(r.free_ranges(0x8C299800, 0x8C2A0000), [])      # font + money + planned bank cover the whole tail
        with self.assertRaises(PE.EngineError):
            r.alloc('hooks', 'hook', 0x40, 0x8C299800, 0x8C2A0000)
        del r.caves['bank']                                               # the bank owner would carve its own pieces
        self.assertEqual(r.free_ranges(0x8C299800, 0x8C2A0000), [(0x8C299C00, 0x8C2A0000)])
        c = r.alloc('hooks', 'hook', 0x41, 0x8C299800, 0x8C2A0000, align=16)
        self.assertEqual((c.addr, c.size), (0x8C299C00, 0x41))
        d = r.alloc('more', 'hook', 0x10, 0x8C299800, 0x8C2A0000, align=16)
        self.assertEqual(d.addr, 0x8C299C50)
        with self.assertRaises(PE.EngineError):
            r.alloc('huge', 'hook', 0x10000, 0x8C299800, 0x8C2A0000)

    def test_symbols(self):
        r = PE.default_registry()
        r.define('font.adv_A', 0x8C299800)
        r.define('font.adv_A', 0x8C299800)
        with self.assertRaises(PE.EngineError):
            r.define('font.adv_A', 0x8C299804)
        self.assertEqual(r.resolve('font.adv_A'), 0x8C299800)
        with self.assertRaises(PE.EngineError):
            r.resolve('nope')

    def test_check_zero(self):
        r = PE.default_registry()
        k = bytearray(0x290000)
        r.check_zero(bytes(k), 'font.cave')
        k[0x299800 - 0x10000 + 5] = 1
        with self.assertRaises(PE.EngineError):
            r.check_zero(bytes(k), 'font.cave')
        r.check_zero(bytes(k), 'money.cave')
        with self.assertRaises(PE.EngineError):
            r.check_zero(b'', 'money.cave')                      # outside the file


# ------------------------------------------------------------------------------------------------ edit set
class Edits(unittest.TestCase):
    def test_apply_and_order_independence(self):
        d = bytes(range(64))
        a = PE.EditSet()
        a.add('x', 'f', 4, b'\xAA\xBB', expect=d[4:6])
        a.add('y', 'f', 10, b'\xCC', expect=d[10:11])
        b = PE.EditSet()
        b.add('y', 'f', 10, b'\xCC')
        b.add('x', 'f', 4, b'\xAA\xBB')
        ra, rb = a.apply({'f': d}), b.apply({'f': d})
        self.assertEqual(ra, rb)
        self.assertEqual(len(ra['f']), 64)
        self.assertEqual(ra['f'][4:6] + ra['f'][10:11], b'\xAA\xBB\xCC')
        PE.verify_confined(d, ra['f'], a, 'f')
        with self.assertRaises(PE.EngineError):
            PE.verify_confined(d, ra['f'] + b'\0', a, 'f')                # size change
        e = PE.EditSet()
        e.add('x', 'f', 4, b'\xAA')
        with self.assertRaises(PE.EngineError):
            PE.verify_confined(d, ra['f'], e, 'f')              # byte 5 and 10 changed outside the declared range

    def test_overlap_is_refused(self):
        es = PE.EditSet()
        es.add('font', 'f', 8, bytes(16))
        es.add('money', 'f', 20, bytes(8))                      # 8..24 vs 20..28
        with self.assertRaises(PE.EngineError) as c:
            es.apply({'f': bytes(64)})
        self.assertIn('overlapping', str(c.exception))
        es = PE.EditSet()
        es.add('font', 'f', 8, bytes(16))
        es.add('money', 'f', 24, bytes(8))                      # adjacent is fine
        es.apply({'f': bytes(64)})
        es = PE.EditSet()
        es.add('a', 'f', 8, b'\1\2')
        es.add('a', 'f', 8, b'\1\2')                            # identical duplicate of one owner: tolerated
        es.apply({'f': bytes(16)})
        es.add('a', 'f', 8, b'\1\3')                            # same place, other bytes: refused even for one owner
        with self.assertRaises(PE.EngineError):
            es.apply({'f': bytes(16)})
        es = PE.EditSet()
        es.add('a', 'f', 8, b'\1')
        es.add('b', 'g', 8, b'\2')                              # other file: no conflict
        self.assertEqual(sorted(es.apply({'f': bytes(16), 'g': bytes(16)})), ['f', 'g'])

    def test_expectations_and_bounds(self):
        es = PE.EditSet({'k': 0x1000})
        es.add('x', 'k', 4, b'\1\1', expect=PE.ZERO)
        self.assertEqual(es.apply({'k': bytes(16)})['k'][4:6], b'\1\1')
        with self.assertRaises(PE.EngineError) as c:
            es.apply({'k': b'\0\0\0\0\0\2' + bytes(10)})
        self.assertIn('0x1004', str(c.exception))               # messages print load addresses
        es = PE.EditSet()
        es.add('x', 'k', 4, b'\1', expect=b'\7')
        with self.assertRaises(PE.EngineError):
            es.apply({'k': bytes(16)})
        es = PE.EditSet()
        es.add('x', 'k', 15, b'\1\1')
        with self.assertRaises(PE.EngineError):
            es.apply({'k': bytes(16)})                           # runs past the end
        with self.assertRaises(PE.EngineError):
            es.apply({})                                         # unknown file


# ------------------------------------------------------------------------------------------------ families
HEAD = bytes.fromhex('e62fd62fc62fb62f224ff87f6e90436e39d338dc522fe11f')


class Families(unittest.TestCase):
    def test_mask_rule(self):
        self.assertEqual(PE.mask_bytes(bytes.fromhex('6e90'), 'pc+bsr'), bytes.fromhex('0090'))        # 0x906e: mov.w @(d,pc): d masked
        self.assertEqual(PE.mask_bytes(bytes.fromhex('39d3'), 'pc+bsr'), bytes.fromhex('00d3'))
        self.assertEqual(PE.mask_bytes(bytes.fromhex('12b5'), 'pc+bsr'), bytes.fromhex('00b0'))        # bsr: 12 bit displacement
        self.assertEqual(PE.mask_bytes(bytes.fromhex('12a5'), 'pc+bsr'), bytes.fromhex('12a5'))        # bra only in rule 'branch'
        self.assertEqual(PE.mask_bytes(bytes.fromhex('12a5'), 'branch'), bytes.fromhex('00a0'))
        self.assertEqual(PE.mask_bytes(bytes.fromhex('0589'), 'branch'), bytes.fromhex('0089'))        # bt
        self.assertEqual(PE.mask_bytes(bytes.fromhex('0589'), 'pc+bsr'), bytes.fromhex('0589'))
        self.assertEqual(PE.mask_bytes(bytes.fromhex('6e90'), 'none'), bytes.fromhex('6e90'))
        self.assertEqual(MP._mask(bytes(range(40))), PE.mask_bytes(bytes(range(40)), 'pc+bsr'))        # moneypatch keeps its masked hashes

    def test_head_minimum(self):
        with self.assertRaises(PE.EngineError):
            PE.Family('short', HEAD[:22])
        with self.assertRaises(PE.EngineError):
            PE.Family('odd', HEAD + b'\x00')
        with self.assertRaises(PE.EngineError):
            PE.Family('badrule', HEAD, rule='nope')
        with self.assertRaises(PE.EngineError):
            PE.Family('vague', bytes.fromhex('0090') * 12)          # all masked: no anchor
        with self.assertRaises(PE.EngineError):
            PE.Family('exact15', HEAD[:14], rule='none')
        PE.Family('ok', HEAD[:24])
        PE.Family('exact16', HEAD[:16], rule='none')

    def test_find_with_masked_operands_and_counts(self):
        fam = PE.Family('t', HEAD, align=4, expect={None: 2})
        var = bytearray(HEAD)
        var[12], var[16], var[18] = 0x69, 0x36, 0x35             # other pc displacements (masked)
        img = bytearray(200)
        img[8:32] = HEAD
        img[100:124] = var
        sites = fam.find(bytes(img), 'img')
        self.assertEqual([s.off for s in sites], [8, 100])
        fam.check_count({None: 2})
        with self.assertRaises(PE.EngineError):
            fam.check_count({None: 3})
        img2 = bytearray(img)
        img2[100 + 6] ^= 1                                       # an unmasked byte differs: no longer a copy
        self.assertEqual([s.off for s in fam.find(bytes(img2))], [8])
        img3 = bytearray(img)
        img3[8 + 23] = 0                                         # the last byte of the 24 byte head is significant
        self.assertEqual([s.off for s in fam.find(bytes(img3))], [100])

    def test_variants_alignment_and_lookalikes(self):
        body = HEAD + bytes(range(1, 40))
        key = hashlib.sha1(PE.mask_bytes(body, 'pc+bsr')).hexdigest()[:10]
        fam = PE.Family('v', HEAD, variants={key: 'A'}, body_len=len(body))
        img = bytes(8) + body + bytes(20)
        self.assertEqual([(s.off, s.variant) for s in fam.find(img)], [(8, 'A')])
        bad = bytearray(img)
        bad[8 + 40] ^= 0xFF                                       # body differs after the head
        with self.assertRaises(PE.EngineError) as c:
            fam.find(bytes(bad), 'f.bin')
        self.assertIn('look-alike', str(c.exception))
        mis = bytes(10) + body + bytes(20)
        with self.assertRaises(PE.EngineError):
            fam.find(mis)                                         # offset 10 is not 4-aligned
        skip = PE.Family('s', HEAD, align=4, misaligned='skip')
        self.assertEqual(skip.find(mis), [])
        self.assertEqual(len(PE.Family('s2', HEAD, align=2).find(mis)), 1)
        self.assertEqual(PE.family_tsv(skip.find(bytes(8) + body, 'f')), 'f\t0x8\t')

    def test_scan_family_over_images(self):
        fam = PE.Family('t', HEAD, expect=2)
        imgs = {'a': bytes(4) + HEAD, 'b': bytes(8) + HEAD + HEAD[:0], 'c': bytes(30)}
        sites, cnt = PE.scan_family(fam, imgs)
        self.assertEqual((len(sites), cnt), (2, {None: 2}))
        with self.assertRaises(PE.EngineError):
            PE.scan_family(fam, {'a': bytes(4) + HEAD})

    @unittest.skipUnless(HAVE_EXTRACTED, 'needs extracted/')
    def test_real_families(self):
        fam = MP.FAMILY
        imgs = {rel: MP.read_extracted(rel) for rel in MP.overlay_paths()}
        sites, cnt = PE.scan_family(fam, imgs)
        self.assertEqual(cnt, MP.EXPECTED_SITES)
        self.assertEqual(len(sites), 108)
        # the 24 byte masked head alone selects exactly the same offsets as the old 12 byte prologue + two word test
        for rel, d in imgs.items():
            old, pos = [], 0
            while True:
                i = d.find(MP.PROLOGUE, pos)
                if i < 0:
                    break
                pos = i + 2
                if i + 16 <= len(d) and d[i + 13] == 0x90 and d[i + 14:i + 16] == b'\x43\x6e':
                    old.append(i)
            self.assertEqual([s.off for s in fam.find(d, rel)], old, rel)


# ------------------------------------------------------------------------------------------------ font / money on the engine
@unittest.skipUnless(HAVE_EXTRACTED, 'needs extracted/')
class OnEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = FP.read_extracted('1ST_READ.BIN')

    def test_zero_checks_and_messages(self):
        tbl = bytes([12]) * 256
        k = FP.patch_1st_read(self.k, tbl)
        with self.assertRaises(FP.FontPatchError) as c:
            FP.patch_1st_read(k, tbl)
        self.assertIn('is not zero', str(c.exception))
        k2 = MP.patch_1st_read(self.k)
        with self.assertRaises(MP.MoneyPatchError) as c:
            MP.patch_1st_read(k2)
        self.assertIn('is not zero', str(c.exception))

    def test_font_and_money_compose_in_either_order(self):
        tbl = bytes([12]) * 256
        a = MP.patch_1st_read(FP.patch_1st_read(self.k, tbl))
        b = FP.patch_1st_read(MP.patch_1st_read(self.k), tbl)
        self.assertEqual(a, b)
        diff = [i for i in range(len(a)) if a[i] != self.k[i]]
        lo, hi = 0x8C299400 - FP.IMG_BASE, PE.REGISTRY['bank'].addr - FP.IMG_BASE      # money.lib + font.align + font + money + money.libn (mn6); the bank starts behind
        self.assertTrue(diff and min(diff) >= lo and max(diff) < hi)       # nothing outside font + money, nothing in the bank

    def test_foreign_addresses_are_checked_against_the_registry(self):
        with self.assertRaises(MP.MoneyPatchError):
            MP.patch_1st_read(self.k, 0x8C299800)                          # the font cave
        with self.assertRaises(MP.MoneyPatchError):
            MP.patch_1st_read(self.k, 0x8C299C00 - 0x100)                  # straddles the font table / money cave
        with self.assertRaises(MP.MoneyPatchError):
            MP.patch_1st_read(self.k, 0x8C29A000)                          # inside the planned bank
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(self.k, bytes(256), (0x8C299A00, 0x8C299B00))

    def test_font_gap1_placement_and_overlap(self):
        k = FP.patch_1st_read(self.k, bytes([12]) * 256, 'gap1')
        self.assertNotEqual(k, self.k)
        with self.assertRaises(FP.FontPatchError):
            FP.patch_1st_read(self.k, bytes([12]) * 256, 'gap1', scale=True)   # 144 byte cave does not fit the 128 byte gap1 reserve

    def test_overlay_hooks_are_unchanged_by_prop_scale(self):
        rel = 'FLOW_PRG/MEETING.BIN'
        o1, r1 = FP.make_patches(FP.read_extracted, paths=[rel], glyphs=False)
        o2, r2 = FP.make_patches(FP.read_extracted, paths=[rel], glyphs=False, prop_scale=True)
        self.assertEqual(o1['/' + rel], o2['/' + rel])
        self.assertEqual(o1.keys(), o2.keys())
        self.assertNotEqual(o1['/1ST_READ.BIN'], o2['/1ST_READ.BIN'])
        self.assertEqual((r1['prop_scale'], r2['prop_scale']), (False, True))
        a, b = o1['/1ST_READ.BIN'], o2['/1ST_READ.BIN']
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        self.assertTrue(min(diff) >= 0x8C299800 - FP.IMG_BASE and max(diff) < 0x8C299900 - FP.IMG_BASE)

    def test_default_make_patches_has_no_prop_scale(self):
        out, rep = FP.make_patches(FP.read_extracted, paths=[], glyphs=False)
        k = out['/1ST_READ.BIN']
        o = 0x8C299800 - FP.IMG_BASE
        self.assertEqual(k[o:o + FP.CAVE_SIZE], FP.cave_bytes(FP.PLACEMENTS['tail']))
        self.assertFalse(any(k[o + FP.CAVE_SIZE:o + FP.RESERVE]))


# ------------------------------------------------------------------------------------------------ --prop-scale cave in the interpreter
CAVE, TABLE, WIN = 0x8C299800, 0x8C299900, 0x00100000
RET = 0x00002000
WINDOW_VAR = {'A': dict(adv=62, W=60, flag=69, x0=74, entry_adv=FP.ENTRY_ADV_A, entry_wrap=FP.ENTRY_WRAP_A),
              'B': dict(adv=54, W=52, flag=61, x0=66, entry_adv=FP.ENTRY_ADV_B, entry_wrap=FP.ENTRY_WRAP_B)}


def machine(scale, table):
    m = sh4sim.Machine()
    m.load(CAVE, FP.cave_bytes((CAVE, TABLE), scale=scale))
    m.load(TABLE, table)
    return m


def advance(m, var, code, a):
    v = WINDOW_VAR[var]
    m.mem[WIN + v['adv']] = a & 0xFF
    m.R[14], m.R[4], m.PR = WIN, code, RET
    m.run(CAVE + v['entry_adv'], RET)
    return m.R[0]


def ref_advance(table, code, a):
    """the specification of the cave's advance routine for a window advance a > 0 (signed byte): table 0 = 12 px,
    A = 24 uses the table as is, any other A scales it, w = (t * A + 12) / 24"""
    t = table[code & 0xFF] or 12
    return t if a == 24 else (t * a + 12) // 24


def orig_rule(a):
    a = a - 256 if a >= 128 else a
    return ((a + (1 if a < 0 else 0)) >> 1) & 0xFFFFFFFF


class PropScale(unittest.TestCase):
    rnd = random.Random(7)

    def tables(self):
        t1 = bytes(self.rnd.randint(0, 24) for _ in range(256))
        t2 = bytes([12]) * 256
        t3 = bytes(([0] * 4 + [24] * 4 + [1] * 4 + [13] * 4) * 16)
        out = [t1, t2, t3]
        if HAVE_EXTRACTED:
            import font as F
            f = FP.read_extracted('FONT.BIN')
            out.append(FP.proportional_font(f, F.Font(f).half())[1])
        return out

    def test_reciprocal_is_exact(self):
        for x in range(0, 4000):
            self.assertEqual((x * 2731) >> 16, x // 24, x)
        self.assertEqual(24 * 127 + 12, 3060)

    def test_cave_layout(self):
        d, s = FP.cave_bytes((CAVE, TABLE)), FP.cave_bytes((CAVE, TABLE), scale=True)
        self.assertEqual((len(d), len(s)), (FP.CAVE_SIZE, FP.CAVE_SIZE_SCALE))
        self.assertLessEqual(len(s), FP.RESERVE)
        diff = [i for i in range(len(d)) if d[i] != s[i]]
        self.assertEqual(diff, [FP.ADV_BF_OFF])                    # exactly one byte of the default cave differs (the bf displacement)
        self.assertEqual(s[FP.ADV_BF_OFF + 1], d[FP.ADV_BF_OFF + 1])
        # the default part keeps the table literal at +100 and all entry offsets
        self.assertEqual(struct.unpack_from('<I', s, 100)[0], TABLE)
        self.assertEqual(struct.unpack_from('<I', s, len(s) - 4)[0], TABLE)
        # an independent assembly of the whole scale cave from source (listing = fontcheck's CAVE_SRC) is not repeated here; the decode is:
        if MD is not None:
            text = {}
            for i in range(FP.CAVE_SIZE, len(s) - 4, 2):
                ins = list(MD.disasm(s[i:i + 2], CAVE + i))
                text[i] = ('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip() if ins else '.word'
            self.assertIn('cmp/pl r2', text.values())
            self.assertIn('mul.l r2,r0', text.values())
            self.assertIn('shlr16 r0', text.values())
            ins = list(MD.disasm(s[FP.ADV_BF_OFF:FP.ADV_BF_OFF + 2], CAVE + FP.ADV_BF_OFF))[0]
            self.assertEqual(ins.mnemonic, 'bf')
            self.assertEqual(int(ins.op_str, 16), CAVE + FP.CAVE_SIZE)      # now branches to the appended routine
        # every other word of the default cave decodes identically
        self.assertEqual(s[:FP.ADV_BF_OFF] + s[FP.ADV_BF_OFF + 2:FP.CAVE_SIZE], d[:FP.ADV_BF_OFF] + d[FP.ADV_BF_OFF + 2:])

    def test_advance_matches_reference_for_every_window_advance(self):
        for table in self.tables():
            m = machine(True, table)
            for a in range(-128, 128):
                for code in [0, 0x20, 0x21, 0x30, 0x39, 0x41, 0x57, 0x6D, 0x7E, 0x80, 0xA1, 0xDF, 0xFF] + [self.rnd.randrange(256) for _ in range(20)]:
                    want = ref_advance(table, code, a & 0xFF) if a > 0 else orig_rule(a & 0xFF)
                    self.assertEqual(advance(m, 'A', code, a & 0xFF), want, 'A=%d code=%#x' % (a, code))

    def test_variant_b_entry(self):
        table = self.tables()[0]
        m = machine(True, table)
        for a in (10, 16, 24, 32, 48, 0, -4, 127):
            for code in range(0, 256, 5):
                want = ref_advance(table, code, a & 0xFF) if a > 0 else orig_rule(a & 0xFF)
                self.assertEqual(advance(m, 'B', code, a & 0xFF), want, 'B A=%d code=%#x' % (a, code))

    def test_identity_for_twelve_and_default_behaviour_kept(self):
        """table 12 (digits, unlisted codes) scales exactly like the original A >> 1; A = 24 and A <= 0 are the default cave"""
        t12 = bytes([12]) * 256
        tb = self.tables()[0]
        ms, md = machine(True, tb), machine(False, tb)
        for a in list(range(-128, 1)) + [24]:
            for code in (0x21, 0x41, 0xA5):
                self.assertEqual(advance(ms, 'A', code, a & 0xFF), advance(md, 'A', code, a & 0xFF), (a, code))
        m12 = machine(True, t12)
        for a in range(1, 128):
            # (12 * A + 12) / 24 = (A + 1) >> 1: equal to the original A >> 1 for every EVEN advance (all real windows: 10 16 32 48),
            # one pixel more for an odd one
            self.assertEqual(advance(m12, 'A', 0x41, a), (a + 1) >> 1 if a != 24 else 12, a)
            if a % 2 == 0:
                self.assertEqual(advance(m12, 'A', 0x41, a), a >> 1 if a != 24 else 12, a)

    def test_wrap_routine_is_untouched(self):
        table = self.tables()[0]
        ms, md = machine(True, table), machine(False, table)
        for var in ('A', 'B'):
            v = WINDOW_VAR[var]
            for _ in range(400):
                a = self.rnd.choice([10, 16, 24, 32, 48, self.rnd.randrange(1, 60)])
                W = self.rnd.randrange(1, 45)
                flag = self.rnd.choice([0, 1])
                x0 = self.rnd.randrange(0, 200)
                x = x0 + self.rnd.randrange(0, 1100)
                code = self.rnd.choice([0x41, 0x4141, 0x2020, 0x8000, 0x4021, self.rnd.randrange(0x10000)])
                res = []
                for m in (ms, md):
                    m.mem[WIN + v['adv']] = a
                    m.mem[WIN + v['W']] = W
                    m.mem[WIN + v['flag']] = flag
                    m.wn(WIN + v['x0'], x0, 2)
                    m.R[14], m.R[4], m.R[5], m.PR = WIN, x, code, RET
                    m.run(CAVE + v['entry_wrap'], RET)
                    res.append(m.R[0])
                self.assertEqual(res[0], res[1])
                self.assertIn(res[0], (0, 1))


if __name__ == '__main__':
    unittest.main()
