"""Unit checks of the money styles and of the TV station card capital patch (tools/moneypatch.py, TV_CARD).  The executed checks
(cave + routine in tools/sh4sim.py, every style) are sections 4 and 7 of tools/moneycheck.py.
    python -I -X utf8 tools/test_moneypatch_tv.py"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moneypatch as MP      # noqa: E402
import pixelwidth as PX      # noqa: E402


class Styles(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(MP.STYLES, ('jp', 'western'))
        self.assertEqual(MP.DEFAULT_STYLE, 'jp')
        with self.assertRaises(MP.MoneyPatchError):
            MP.cave_bytes(MP.CAVE_ADDR, 'metric')
        with self.assertRaises(MP.MoneyPatchError):
            MP.reference(1, 0, 'metric')

    def test_jp_reference_examples(self):
        for v, want in ((0, '0 Yen'), (1, '1 man'), (15, '15 man'), (6000, '6000 man'), (9999, '9999 man'), (10000, '1 oku'),
                        (10300, '1 oku 300 man'), (10001, '1 oku 1 man'), (100050, '10 oku 50 man'), (131500, '13 oku 1500 man'),
                        (815000, '81 oku 5000 man'), (990000, '99 oku'), (-50, '-50 man'), (-131500, '-13 oku 1500 man'),
                        (99999999, '9999 oku 9999 man'), (2 ** 31 - 1, '214748 oku 3647 man'), (-2 ** 31, '-214748 oku 3648 man')):
            self.assertEqual(MP.reference(v), want)
            self.assertEqual(MP.reference(v, 0, 'jp'), want)
            self.assertEqual(MP.reference(v, 1, 'jp'), want)          # the flag is ignored in jp

    def test_jp_reference_is_exact(self):
        import re
        for v in list(range(0, 30001, 7)) + [10 ** k + d for k in range(4, 10) for d in (-1, 0, 1, 5000)]:
            t = MP.reference(v)
            if v == 0:
                self.assertEqual(t, '0 Yen')
                continue
            m = re.match(r'^(?:([1-9]\d*) oku)?(?: )?(?:([1-9]\d{0,3}) man)?$', t)
            self.assertTrue(m, t)
            self.assertEqual(int(m.group(1) or 0) * 10 ** 4 + int(m.group(2) or 0), v)

    def test_western_reference_unchanged(self):
        for v, flag, want in ((0, 0, 'Y0'), (15, 0, 'Y150k'), (150, 0, 'Y1.5M'), (6000, 0, 'Y60M'), (131500, 0, 'Y1.315bn'),
                              (815000, 0, 'Y8.15bn'), (100050, 0, 'Y1000.5M'), (-150, 0, '-Y1.5M'), (131500, 1, 'Y1315000000')):
            self.assertEqual(MP.reference(v, flag, 'western'), want)

    def test_caves(self):
        jp, we = MP.cave_bytes(MP.CAVE_ADDR, 'jp'), MP.cave_bytes(MP.CAVE_ADDR, 'western')
        self.assertEqual(MP.cave_bytes(), jp)
        self.assertEqual(len(we), 428)                                 # the historic western cave, byte for byte (tools/re/mny_baseline_cmp.py)
        self.assertLess(len(jp), len(we))
        self.assertLessEqual(len(jp), MP.RESERVE)
        self.assertNotEqual(jp, we)
        self.assertEqual(MP.cave_symbols(MP.CAVE_ADDR, 'western')['m_dec'], MP.CAVE_ADDR + 0x136)
        self.assertEqual(MP.cave_symbols(MP.CAVE_ADDR, 'jp')['money'], MP.CAVE_ADDR)

    def test_make_patches_style(self):
        rel = 'FLOW_PRG/MEETING.BIN'
        a, ra = MP.make_patches(MP.read_extracted, paths=[rel])
        b, rb = MP.make_patches(MP.read_extracted, paths=[rel], style='western')
        c, rc = MP.make_patches(MP.read_extracted, paths=[rel], style='jp')
        self.assertEqual((ra['style'], rb['style']), ('jp', 'western'))
        self.assertEqual(a, c)
        self.assertNotEqual(a['/1ST_READ.BIN'], b['/1ST_READ.BIN'])
        self.assertEqual(rb['size'], 428)
        # the %D literal points at the m_dec of the style
        ov = MP.read_extracted(rel)
        site = MP.find_sites(ov)[0]['off']
        lit = MP.find_d_literal(ov, site)[0]
        self.assertEqual(struct.unpack_from('<I', a['/' + rel], lit)[0], MP.cave_symbols(MP.CAVE_ADDR, 'jp')['m_dec'])
        self.assertEqual(struct.unpack_from('<I', b['/' + rel], lit)[0], MP.cave_symbols(MP.CAVE_ADDR, 'western')['m_dec'])


class TvCard(unittest.TestCase):
    def setUp(self):
        self.d = MP.read_extracted(MP.TV_CARD['rel'])

    def test_signature_and_size(self):
        self.assertEqual(MP.tv_card_sig(self.d), MP.TV_CARD_SIG)
        for style in MP.STYLES:
            code, tail, _ = MP.tv_card_bytes(0x8C2D33C0, style)
            self.assertEqual(len(code), MP.TV_CARD['fn_end'] - MP.TV_CARD['fn'])
            self.assertEqual(len(tail), MP.TV_CARD['tail_end'] - MP.TV_CARD['tail'])

    def test_jp_routine_is_the_western_one_plus_x_shift_and_bigger_buffer(self):
        cj, _, ij = MP.tv_card_bytes(0x8C2D33C0, 'jp')
        cw, _, iw = MP.tv_card_bytes(0x8C2D33C0, 'western')
        tj = [t for _, _, t in ij]
        tw = [t for _, _, t in iw]
        self.assertIn('add #%d,r13' % (MP.TV_CARD_X_JP - 512), tj)
        self.assertIn('mov #77,r6', tj)                       # compact form: '32 oku 5000m'
        self.assertIn('add #-32,r15', tj)
        self.assertIn('add #32,r15', tj)
        self.assertNotIn('add #%d,r13' % (MP.TV_CARD_X_JP - 512), tw)
        self.assertIn('mov #0,r6', tw)
        self.assertIn('add #-16,r15', tw)
        self.assertEqual(len(tj), len(tw) + 1)
        self.assertNotEqual(cj, cw)

    def test_patch_confined_and_not_repeatable(self):
        site = MP.find_sites(self.d)[0]['off']
        for style in MP.STYLES:
            nd = MP.patch_tv_card(self.d, site, style=style)
            t = MP.TV_CARD
            diff = [i for i in range(len(nd)) if nd[i] != self.d[i]]
            self.assertTrue(diff and min(diff) >= t['fn'] and max(diff) < t['tail_end'])
            self.assertFalse(any(t['fn_end'] <= i < t['tail'] for i in diff))
            self.assertEqual(struct.unpack_from('<I', nd, t['tail'])[0], t['base'] + site)
            with self.assertRaises(MP.MoneyPatchError):
                MP.patch_tv_card(nd, site, style=style)

    def test_make_patches_hooks_tv_event(self):
        for style in MP.STYLES:
            out, rep = MP.make_patches(MP.read_extracted, paths=[MP.TV_CARD['rel']], style=style)
            self.assertEqual(rep.get('tv_card'), MP.TV_CARD['rel'])
            self.assertNotEqual(out['/' + MP.TV_CARD['rel']], self.d)
            out2, rep2 = MP.make_patches(MP.read_extracted, paths=[MP.TV_CARD['rel']], tv_card=False, style=style)
            self.assertNotIn('tv_card', rep2)
            self.assertNotEqual(out['/' + MP.TV_CARD['rel']], out2['/' + MP.TV_CARD['rel']])
        a, _ = MP.make_patches(MP.read_extracted, paths=[MP.TV_CARD['rel']], style='jp')
        b, _ = MP.make_patches(MP.read_extracted, paths=[MP.TV_CARD['rel']], style='western')
        self.assertNotEqual(a['/' + MP.TV_CARD['rel']], b['/' + MP.TV_CARD['rel']])

    def test_capital_values(self):
        want = {325000: '32 oku 5000 man', 650000: '65 oku', 2270000: '227 oku', 4410000: '441 oku', 8340000: '834 oku', 9450000: '945 oku'}
        west = {325000: 'Y3.25bn', 650000: 'Y6.5bn', 2270000: 'Y22.7bn', 4410000: 'Y44.1bn', 8340000: 'Y83.4bn', 9450000: 'Y94.5bn'}
        for v in want:
            self.assertEqual(MP.reference(v), want[v])
            self.assertEqual(MP.reference(v, 0, 'western'), west[v])

    def test_capital_fits_the_plate(self):
        """the compact capital text (flag 77) starts at x = 456 and must end before the plate edge (616) of the TV card; the full form would not."""
        x0 = MP.TV_CARD_X_JP
        for v in (325000, 650000, 2270000, 4410000, 8340000, 9450000):
            end = PX.line_px(MP.reference(v, MP.COMPACT_FLAG))[0]
            self.assertLessEqual(x0 + end, 616, MP.reference(v))
        self.assertGreater(448 + PX.line_px("32 oku 5000 man")[0], 616)       # why the full form does not do


class Compact(unittest.TestCase):
    """the compact output (flag COMPACT_FLAG = 'M'): reference, panel call sites, the `%M` expander token, validators."""

    def test_reference(self):
        F = MP.COMPACT_FLAG
        self.assertEqual(F, ord('M'))
        for v, want in ((0, '0 Yen'), (15, '15 man'), (6000, '6000 man'), (10000, '1 oku'), (990000, '99 oku'),            # one part: unchanged
                        (10300, '1 oku 300m'), (10001, '1 oku 1m'), (131500, '13 oku 1500m'), (-131500, '-13 oku 1500m'),
                        (999 * 10000 + 9999, '999 oku 9999m'), (99999999, '9999 oku 9999m')):
            self.assertEqual(MP.reference(v, F, 'jp'), want)
        for v in (1, 10300, 131500, 2 ** 31 - 1, -2 ** 31):
            self.assertEqual(MP.reference(v, 0, 'jp'), MP.reference(v, 1, 'jp'))        # the old flags still mean "full"
        self.assertLessEqual(max(len(MP.reference(100 * w, F, 'jp')) for w in range(1, 10000)), 12)   # the 12 byte panel field, below 100 oku
        self.assertEqual(MP.reference(10300, F, 'western'), 'Y103000000')           # western: any flag != 0 is "exact yen", so it never gets the token
        self.assertEqual(len(MP.cave_bytes(MP.CAVE_ADDR, 'jp')), 388)
        self.assertLessEqual(len(MP.cave_bytes(MP.CAVE_ADDR, 'jp')), MP.RESERVE)

    def test_panel_sites_and_defaults(self):
        for rel in ('FLOW_PRG/SCDRF.BIN', 'FLOW_PRG/SEARCH.BIN'):
            d = MP.read_extracted(rel)
            on, sites = MP.patch_overlay(d, rel)                                   # panel_compact default ON, token default OFF
            off, _ = MP.patch_overlay(d, rel, panel_compact=False)
            self.assertEqual(len(sites[0]['panel']), 2)
            self.assertEqual(len(on), len(d))
            for o in sites[0]['panel']:
                self.assertEqual(on[o:o + 2], struct.pack('<H', 0xE600 | MP.COMPACT_FLAG))
                self.assertEqual(off[o:o + 2], struct.pack('<H', 0xE600))
            self.assertEqual(sum(1 for a, b in zip(on, off) if a != b), 2)
            wd, ws = MP.patch_overlay(d, rel, style='western')
            self.assertEqual(ws[0]['panel'], [])                                   # western: nothing compact
        other, sites = MP.patch_overlay(MP.read_extracted('FLOW_PRG/MEETING.BIN'), 'FLOW_PRG/MEETING.BIN')
        self.assertEqual(sites[0]['panel'], [])

    def test_expander_token(self):
        rel = 'FLOW_PRG/MEETING.BIN'
        d = MP.read_extracted(rel)
        base, _ = MP.patch_overlay(d, rel)
        tok, sites = MP.patch_overlay(d, rel, compact_token=True)
        diff = [i for i in range(len(d)) if base[i] != tok[i]]
        start = sites[0]['dlit'] - MP.EXP_DLIT_REL
        self.assertTrue(all(start + MP.EXP_CHAIN_REL <= i < start + MP.EXP_CHAIN_REL + 20 or start + MP.EXP_R6_REL <= i < start + MP.EXP_R6_REL + 2 for i in diff))
        self.assertEqual(len(MP._chain_words(True)), 20)
        self.assertEqual(len(MP._chain_words(False)), 20)
        self.assertEqual(d[start + MP.EXP_CHAIN_REL:start + MP.EXP_CHAIN_REL + 20], MP._chain_words(False))   # the original chain
        w, _ = MP.patch_overlay(d, rel, style='western', compact_token=True)       # western never gets the token
        self.assertEqual(w, MP.patch_overlay(d, rel, style='western')[0])
        out, rep = MP.make_patches(MP.read_extracted, paths=['FLOW_PRG/SCDRF.BIN', rel], compact_token=True)
        self.assertEqual(rep['token_overlays'], 2)
        self.assertEqual(rep['panel_sites'], 2)
        out0, rep0 = MP.make_patches(MP.read_extracted, paths=['FLOW_PRG/SCDRF.BIN', rel])
        self.assertEqual(rep0['token_overlays'], 0)
        self.assertEqual(rep0['panel_sites'], 2)

    def test_validators(self):
        import translib as T
        import transcheck as C
        self.assertEqual(T.tokens_of('Costs %M, was %m.'), ['%M', '%m'])
        self.assertEqual(T.canon_tokens(['%M', '%m', '%d']), ['%m', '%m', '%d'])
        self.assertEqual(T._fmt_cells('%M'), 12)
        self.assertEqual(T._fmt_cells('%m'), 15)
        self.assertEqual(T.printf_order(['%M', '@Y/', '%d']), ['%M', '%d'])
        self.assertLess(PX.line_px('%M')[0], PX.line_px('%m')[0])
        self.assertEqual(PX.line_px('%M')[0], 12 * 12)
        # the browser token set is unchanged: %M is no format there
        self.assertEqual(T.tokens_of('a %M', 'browser'), [])


if __name__ == '__main__':
    unittest.main()
