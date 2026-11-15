"""Checks of tools/textfmt_gap.py (curated overlay strings that the textdb pointer / orphan scan misses).
    python -I -X utf8 tools/test_gap.py          (reads extracted/ and translation/: a few seconds, no build is made)"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import textdb as T          # noqa: E402
import textfmt_common as C  # noqa: E402
import textfmt_gap as G     # noqa: E402


class Render(unittest.TestCase):
    def test_nul_string(self):
        self.assertEqual(G.render('あ', 'Ab', 4, False), b'Ab\0\0\0')       # slot span + 1 = 5

    def test_nul_string_too_long(self):
        with self.assertRaises(ValueError):
            G.render('あ', 'Abcde', 4, False)

    def test_cont_pads_before_last_newline(self):
        out = G.render('xx', 'One\nTwo', 12, True)
        self.assertEqual(len(out), 12)
        self.assertEqual(out, b'One     \nTwo')                  # blanks at the end of the first line, text still joins the tail

    def test_cont_pads_at_end_without_newline(self):
        self.assertEqual(G.render('xx', 'Not', 4, True), b'Not ')

    def test_cont_keeps_trailing_newline_of_the_japanese(self):
        out = G.render('あ\n', 'Hi there.\n', 14, True)
        self.assertEqual(out, b'Hi there.    \n')
        self.assertEqual(len(out), 14)

    def test_cont_too_long(self):
        with self.assertRaises(ValueError):
            G.render('xx', 'Abcd', 4, True)                       # at most span - 1 = 3 bytes


class RealImages(unittest.TestCase):
    def test_every_entry_extracts_and_is_in_the_database(self):
        n = 0
        for source, ents in G.GAPS.items():
            data = open(os.path.join(ROOT, 'extracted', *source.split('/')), 'rb').read()
            recs = G.extract(data, source)
            self.assertEqual(len(recs), len(ents), source)         # none skipped
            db = {}
            for ln in open(os.path.join(ROOT, 'translation', T.jsonl_name(source)), encoding='utf8'):
                r = json.loads(ln)
                db[r['id']] = r
            starts = sorted(T._off(r) for r in db.values() if r.get('fmt') != 'gap')
            for r in recs:
                self.assertIn(r['id'], db)
                self.assertEqual(db[r['id']]['ja'], r['ja'])
                self.assertEqual(db[r['id']]['max_bytes'], r['max_bytes'])
                off = T._off(r)
                if r.get('cont'):
                    self.assertIn(off + r['max_bytes'], starts, '%s must run into the next record' % r['id'])
                else:
                    self.assertEqual(data[off + r['max_bytes'] - 1], 0)
                n += 1
        self.assertEqual(n, 37)

    def test_apply_round_trip_on_nenrep(self):
        source = 'FLOW_PRG/NENREP.BIN'
        data = open(os.path.join(ROOT, 'extracted', *source.split('/')), 'rb').read()
        recs = G.extract(data, source)
        for r in recs:
            r['en'] = 'Ab' if not r.get('cont') else 'A'
        new = G.apply(data, recs)
        self.assertEqual(len(new), len(data))
        changed = [i for i in range(len(data)) if data[i] != new[i]]
        lo = min(T._off(r) for r in recs)
        hi = max(T._off(r) + r['max_bytes'] for r in recs)
        self.assertTrue(all(lo <= i < hi for i in changed))
        for r in recs:
            off = T._off(r)
            if not r.get('cont'):
                self.assertEqual(new[off:off + 3], b'Ab\0')
            else:
                tail = b'\n' if r['ja'].endswith('\n') else b' '          # a Japanese head that ends in a line break keeps one
                self.assertEqual(new[off:off + r['max_bytes']], b'A' + b' ' * (r['max_bytes'] - 2) + tail)

    def test_nenrep_people_formats_fit_their_slots(self):
        """the 8 people formats (0x24f34..0x24f8b): English written in place, every slot keeps its zero padding, nothing leaks into the next string"""
        source = 'FLOW_PRG/NENREP.BIN'
        data = open(os.path.join(ROOT, 'extracted', *source.split('/')), 'rb').read()
        db = {}
        for ln in open(os.path.join(ROOT, 'translation', T.jsonl_name(source)), encoding='utf8'):
            r = json.loads(ln)
            db[r['id']] = r
        recs = [r for r in G.extract(data, source) if 0x24f34 <= T._off(r) < 0x24f8c]
        self.assertEqual([T._off(r) for r in recs], [0x24f34, 0x24f44, 0x24f50, 0x24f5c, 0x24f68, 0x24f74, 0x24f7c, 0x24f84])
        shown = {0x24f34: '@R/%sman %sppl@', 0x24f50: '%sman %sppl', 0x24f68: '@R/%sppl@', 0x24f7c: '%sppl'}      # the four that real() prints
        for r in recs:
            r['en'] = db[r['id']]['en']
            self.assertTrue(r['en'], r['id'])
            self.assertEqual(r['en'].count('%s'), r['ja'].count('%s'), r['id'])             # same arguments as the Japanese
            self.assertEqual(r['en'].startswith('@R/'), r['ja'].startswith('@R/'), r['id'])   # the red form stays the red form
            self.assertEqual(r['en'].endswith('@'), r['ja'].endswith('@'), r['id'])
            if T._off(r) in shown:
                self.assertEqual(r['en'], shown[T._off(r)])
        new = G.apply(data, recs)
        self.assertEqual(len(new), len(data))
        changed = [i for i in range(len(data)) if data[i] != new[i]]
        self.assertTrue(all(0x24f34 <= i < 0x24f8c for i in changed))                       # `ktLoadZarcTexture : %s` at 0x24f8c is untouched
        self.assertEqual(new[0x24f8c:0x24f9c], data[0x24f8c:0x24f9c])
        for r in recs:
            off = T._off(r)
            e = r['en'].encode('cp932')
            self.assertEqual(new[off:off + len(e) + 1], e + b'\0')
            self.assertFalse(any(new[off + len(e) + 1:off + r['max_bytes']]))               # zero padding up to the next string

    def test_stale_text_is_refused(self):
        source = 'FLOW_PRG/HELP.BIN'
        data = bytearray(open(os.path.join(ROOT, 'extracted', *source.split('/')), 'rb').read())
        recs = G.extract(bytes(data), source)
        recs[0]['en'] = 'X'
        data[T._off(recs[0]) + 3] ^= 1
        with self.assertRaises(ValueError):
            G.apply(bytes(data), recs)


if __name__ == '__main__':
    unittest.main()
