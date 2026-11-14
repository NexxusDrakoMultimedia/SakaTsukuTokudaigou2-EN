"""Unit checks of the BCAST.BIN subtitle patch (tools/textfmt_bcast.py, build_patch.do_bcast, discbuild sparse edits).
    python -I -X utf8 tools/test_bcast.py            (reads the original disc tracks: a few seconds; no build is made)"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import textfmt_bcast as B       # noqa: E402
import textfmt_common as C      # noqa: E402


def make_header(name, texts, slots=None):
    h = bytearray(2048)
    h[:16] = B.MAGIC
    h[0x10:0x10 + len(name)] = name.encode()
    h[0x40:0x4a] = b'size:00000\0'
    pos = 0x80
    for i, t in enumerate(texts):
        slot = (slots[i] if slots else ((len(t) + 1 + 15) // 16) * 16)
        struct.pack_into('<I', h, 0x60 + 4 * i, pos)
        h[pos:pos + len(t)] = t
        pos += slot
    return bytes(h)


JA1 = 'そうですね'.encode('cp932')
JA2 = 'なるほど。'.encode('cp932')


class HeaderEdit(unittest.TestCase):
    def test_parse(self):
        h = make_header('yh\\x.p04', [JA1, JA2], [16, 64])
        name, segs = B.header_segments(h)
        self.assertEqual(name, 'yh\\x.p04')
        self.assertEqual([(o, s) for o, s, r in segs], [(0x80, 16), (0x90, 16)])
        self.assertEqual(segs[0][2], JA1)

    def test_in_place(self):
        h = make_header('yh\\x.p04', [JA1, JA2], [16, 64])
        ja = C.decode_text(JA1)
        new, bad, stale = B.apply_to_header(h, {0x80: (ja, "That's right.", 75)})
        self.assertEqual((bad, stale), ([], []))
        self.assertEqual(new[0x60:0x80], h[0x60:0x80])                       # table untouched
        self.assertEqual(new[0x80:0x90], b"That's right.\0\0\0")
        self.assertEqual(new[0x90:], h[0x90:])                               # the other segment untouched

    def test_relaid_out_when_longer_than_the_slot(self):
        h = make_header('yh\\x.p04', [JA1, JA2], [16, 64])
        ja = C.decode_text(JA1)
        en = 'That is right, and I would like to say more about it.'     # 54 > 15
        new, bad, stale = B.apply_to_header(h, {0x80: (ja, en, 75)})
        self.assertEqual((bad, stale), ([], []))
        name, segs = B.header_segments(new)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0][2], en.encode())
        self.assertEqual(segs[1][2], JA2)                                    # unedited segment moved but kept
        self.assertTrue(all(o % 16 == 0 and o >= 0x80 for o, s, r in segs))
        self.assertEqual(new[:0x60], h[:0x60])

    def test_failures(self):
        h = make_header('yh\\x.p04', [JA1], [16])
        ja = C.decode_text(JA1)
        _, bad, stale = B.apply_to_header(h, {0x80: ('違う', 'x', 75)})
        self.assertEqual(len(stale), 1)
        _, bad, stale = B.apply_to_header(h, {0x90: (ja, 'x', 75)})
        self.assertEqual(len(stale), 1)
        _, bad, stale = B.apply_to_header(h, {0x80: (ja, 'a' * 80, 75)})
        self.assertEqual(len(bad), 1)
        _, bad, stale = B.apply_to_header(h, {0x80: (ja, 'two\nlines', 75)})
        self.assertEqual(len(bad), 1)
        _, bad, stale = B.apply_to_header(h, {0x80: (ja, '☃', 75)})
        self.assertEqual(len(bad), 1)
        new, bad, stale = B.apply_to_header(h, {0x80: (ja, 'x' * 74, 75)})
        self.assertEqual((bad, stale), ([], []))                              # 74 + NUL = 75 is the budget

    def test_no_edit_is_identity(self):
        h = make_header('yh\\x.p04', [JA1], [16])
        self.assertEqual(B.apply_to_header(h, {})[0], h)


class RealDisc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = B.read_headers()

    def test_every_header_parses(self):
        self.assertEqual(len(self.rows), 26635)
        for sec, h in self.rows:
            name, segs = B.header_segments(h)
            self.assertTrue(segs, name)
            last = 0
            for o, slot, raw in segs:
                self.assertTrue(o > last and o % 16 == 0 and o + slot <= 2048, (name, o))
                last = o
            self.assertFalse(any(h[j] for j in range(B.TEXT0, 2048) if all(not (o <= j < o + s) for o, s, r in segs)), name)

    def test_extract_round_trip_is_identity(self):
        recs = B.extract(self.rows)
        self.assertEqual(len(recs), 30083)
        by = {}
        for r in recs:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            by.setdefault(off // 2048, {})[off % 2048] = (r['ja'], r['ja'], 4096)
        # writing the Japanese itself (en == ja) must leave every header byte-identical
        n = 0
        for sec, h in self.rows[:2000]:
            new, bad, stale = B.apply_to_header(h, by.get(sec, {}))
            self.assertEqual((bad, stale), ([], []))
            self.assertEqual(new, h)
            n += 1
        self.assertEqual(n, 2000)

    def test_jsonl_consistent_with_the_disc(self):
        by = {}
        for sec, h in self.rows:
            by[sec] = h
        recs = B.read_jsonl(B.JSONL)
        self.assertEqual(len(recs), 30083)
        for r in recs[::7]:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            name, segs = B.header_segments(by[off // 2048])
            seg = {o: raw for o, s, raw in segs}[off % 2048]
            self.assertEqual(C.decode_text(seg), r['ja'])
            if r.get('en'):
                self.assertTrue(len(r['en'].encode('cp932')) + 1 <= r['max_bytes'], r['id'])


def join_clips(clips, lead):
    """what the line engine draws for consecutive clips: the texts one behind the other, a blank at column 0 skipped (--cell-prop)"""
    import build_patch as BP
    s = ''.join(BP.bcast_clip_text(en, ctx, lead) for en, ctx in clips)
    return s.strip(' ')


class ClipSeparator(unittest.TestCase):
    """build_patch.bcast_clip_text: the blank between two consecutive commentary clips (--clip-lead-space)"""
    NAME, TEAM, CLIP = 'clip name\\yh_name_albf_501 seg 0/1 slot 16', 'clip yh\\yh_tm_jlf_0001 seg 0/1 slot 16', 'clip yh\\yh_pass_0001 seg 0/1 slot 64'

    def t(self, en, ctx, lead):
        import build_patch as BP
        return BP.bcast_clip_text(en, ctx, lead)

    def test_leading_mode_is_first_character_only(self):
        for ctx in (self.NAME, self.TEAM, self.CLIP):                       # names and team names are NOT special: they follow `The one to watch,` / `Seoul FC vs`
            self.assertEqual(self.t('Suzuki', ctx, True), ' Suzuki')
            self.assertEqual(self.t('9 points', ctx, True), ' 9 points')
            self.assertEqual(self.t('"Oh?" That sort of moment.', ctx, True), ' "Oh?" That sort of moment.')
            self.assertEqual(self.t('(Tournament name) won.', ctx, True), ' (Tournament name) won.')
            self.assertEqual(self.t('*Ahem* That was close.', ctx, True), ' *Ahem* That was close.')
            self.assertEqual(self.t('has made the national squad.', ctx, True), ' has made the national squad.')
            for glue in (", isn't it?", '. Next', '; how', ': x', '!', '?', ')', "'s play; how was it?"):
                self.assertEqual(self.t(glue, ctx, True), glue)             # continues the previous clip: no blank in front
            self.assertEqual(self.t(' x', ctx, True), ' x')                  # never two
            self.assertFalse(self.t('Grampus', ctx, True).endswith(' '))     # nothing appended: no stray blank after a team / name

    def test_trailing_mode_is_the_old_rule(self):
        self.assertEqual(self.t('Suzuki', self.NAME, False), 'Suzuki')
        self.assertEqual(self.t('Grampus', self.TEAM, False), 'Grampus ')
        self.assertEqual(self.t("That's right.", self.CLIP, False), "That's right. ")
        self.assertEqual(self.t('x ', self.CLIP, False), 'x ')

    def test_joins(self):
        n, t, c = self.NAME, self.TEAM, self.CLIP
        for clips, want in (
                ((('Suzuki', n), ('Cuts it out easily here.', c)), 'Suzuki Cuts it out easily here.'),          # the playtest report: `SuzukiCut out easily here.`
                ((('Grampus', t), (", isn't it?", c)), "Grampus, isn't it?"),                                     # `Grampus ,`
                ((('Grampus', t), ("'s play; how was it?", c)), "Grampus's play; how was it?"),
                ((('First half,', c), ('Suzuki', n), ('has made the national squad.', c)), 'First half, Suzuki has made the national squad.'),
                ((('The one to watch in this match,', c), ('Suzuki', n)), 'The one to watch in this match, Suzuki'),
                ((('Seoul FC vs', t), ('Grampus', t), ('on matchday', c), ('3', c)), 'Seoul FC vs Grampus on matchday 3'),
                ((('The result:', c), ('Win', c)), 'The result: Win'),                                                # clip ending in ':' / ',' then a word clip: exactly one blank
                ((('That is a foul', c), ('.', c)), 'That is a foul.'),
        ):
            self.assertEqual(join_clips(clips, True), want)
            self.assertNotIn('  ', join_clips(clips, True))
        # the old rule: a blank after every clip but a name: the two reported symptoms
        self.assertEqual(join_clips((('Suzuki', n), ('Cuts it out easily here.', c)), False), 'SuzukiCuts it out easily here.')
        self.assertEqual(join_clips((('Grampus', t), (", isn't it?", c)), False), "Grampus , isn't it?")

    def test_every_record_fits_with_its_blank(self):
        """the whole database written in leading mode: no record over its budget (a 15-letter name + blank would need 17 bytes), none starts with a blank already"""
        recs = B.read_jsonl(B.JSONL)
        over = []
        for r in recs:
            en = r.get('en')
            if not en:
                continue
            self.assertFalse(en.startswith(' ') or en.endswith(' '), r['id'])
            txt = self.t(en, r['ctx'], True)
            if len(txt.encode('cp932')) + 1 > r['max_bytes']:
                over.append((r['id'], r['ctx'], en))
        self.assertEqual(over, [])

    def test_clip_start_classes(self):
        """counts that docs/text-sources.md quotes: only these first characters are glue; everything else gets the blank"""
        import build_patch as BP
        recs = [r for r in B.read_jsonl(B.JSONL) if r.get('en')]
        glue = [r for r in recs if r['en'][0] in BP.BCAST_LEAD_GLUE]
        self.assertTrue(all(r['ctx'].split(' ')[1].startswith('yh\\') for r in glue))      # only announcer continuation clips
        self.assertEqual(sorted(r['en'] for r in glue), sorted([", our sponsors for this broadcast.", ", isn't it?", "'s play; how was it?"]))
        self.assertEqual(len([r for r in recs if r['en'][0] in '*"(']), 3)               # opening marks keep their blank
        self.assertEqual(len([r for r in recs if r['en'][0].isdigit()]), 452)            # bare numbers / `9 points` ...

    def test_lead_mode_rewrites_all_headers_in_memory(self):
        """the whole database through apply_to_header in leading mode (all real headers): nothing fails, every segment reads back as the clip text"""
        recs = B.read_jsonl(B.JSONL)
        rows = B.read_headers()
        by = {}
        for r in recs:
            if r.get('en'):
                off = int(r['id'].rsplit('#', 1)[1], 16)
                by.setdefault(off // 2048, {})[off % 2048] = (r['ja'], self.t(r['en'], r['ctx'], True), r['max_bytes'])
        n = 0
        for sec, h in rows:
            todo = by.get(sec)
            if not todo:
                continue
            new, bad, stale = B.apply_to_header(h, todo)
            self.assertEqual((bad, stale), ([], []), sec)
            old_segs = B.header_segments(h)[1]
            new_segs = B.header_segments(new)[1]
            self.assertEqual(len(new_segs), len(old_segs))
            for (o, slot, raw), (o2, slot2, raw2) in zip(old_segs, new_segs):      # same order, the table is rewritten when a clip is re-laid out
                self.assertEqual(raw2, todo[o][1].encode('cp932') if o in todo else raw, (sec, o))
            n += len(todo)
        self.assertEqual(n, len([r for r in recs if r.get('en')]))


class SparseDisc(unittest.TestCase):
    def test_plan_rewrites_only_the_touched_sector(self):
        import discbuild as D
        src = D.Source(ROOT)
        try:
            pvd, rl, rs, recs = D.read_filesystem(src)
            f = [r for r in recs if not r.isdir and r.path.upper() == '/BCAST/BCAST.BIN'][0]
            old = src.read(f.lba, 2048)
            new = bytearray(old)
            new[0x80:0x85] = b'Hello'
            plan = D.plan_patches(src, {}, sparse={'/BCAST/BCAST.BIN': {0: bytes(new)}})
            self.assertEqual(sorted(plan.over), [f.lba])
            self.assertEqual(plan.over[f.lba][0x80:0x85], b'Hello')
            self.assertEqual(plan.new_end, src.end_lba)
            self.assertEqual(plan.moves, [])
            # an edit that is not sector-aligned keeps the rest of the sector
            plan = D.plan_patches(src, {}, sparse={'/BCAST/BCAST.BIN': {0x81: b'Z'}})
            self.assertEqual(plan.over[f.lba][0x80], old[0x80])
            self.assertEqual(plan.over[f.lba][0x81], ord('Z'))
            # refusals
            with self.assertRaises(D.DiscError):
                D.plan_patches(src, {'/BCAST/BCAST.BIN': b'x'}, sparse={'/BCAST/BCAST.BIN': {0: b'x'}})
            with self.assertRaises(D.DiscError):
                D.plan_patches(src, {}, sparse={'/BCAST/BCAST.BIN': {f.size: b'x'}})
            with self.assertRaises(KeyError):
                D.plan_patches(src, {}, sparse={'/NOPE.BIN': {0: b'x'}})
            # default: no sparse, nothing rewritten
            self.assertFalse(D.plan_patches(src, {}).over)
        finally:
            src.close()


if __name__ == '__main__':
    unittest.main(verbosity=1)
