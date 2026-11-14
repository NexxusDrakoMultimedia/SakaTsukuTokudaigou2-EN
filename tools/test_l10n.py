# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Tests of tools/l10n.py (the public English + hashes form), tools/verify_source_disc.py and tools/setup_from_disc.py.

    python -I -X utf8 tools/test_l10n.py            # fast subset: synthetic data + a few real files (about 20 s with the real disc)
    python -I -X utf8 tools/test_l10n.py --full     # also the round trip over the WHOLE current tree (snapshot -> export -> import -> byte
                                                    # comparison, determinism, Japanese scan), about 2 minutes; needs the disc in the repo root
Scratch folders are created under build/ (l10n_test_*) and removed afterwards.  Never touches translation/ or l10n/.
"""
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import l10n as L                  # noqa: E402
import verify_source_disc as V    # noqa: E402
import setup_from_disc as S       # noqa: E402

FULL = '--full' in sys.argv
if FULL:
    sys.argv.remove('--full')
EXTRACTED = os.path.join(ROOT, 'extracted')
CUE = os.path.join(ROOT, 'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan).cue')
HAVE_REAL = os.path.isdir(EXTRACTED) and os.path.isfile(CUE)
JP = L.JP_RE

SILENT = lambda *a, **k: None


def jenc(s):
    return s.encode('cp932')


class Scratch(unittest.TestCase):
    def setUp(self):
        os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
        self.tmp = tempfile.mkdtemp(prefix='l10n_test_', dir=os.path.join(ROOT, 'build'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *p):
        return os.path.join(self.tmp, *p)


def write_jsonl(path, recs, style='compact', final_nl=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sep = L.STYLES[style]
    text = '\n'.join(json.dumps(r, ensure_ascii=False, separators=sep) for r in recs) + ('\n' if final_nl else '')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


# ------------------------------------------------------------------------------------------- synthetic disc
def build_fake():
    """-> (files {source: bytes}, records {file name: [records]}, bcast headers)"""
    ov = bytearray(0x100)
    a = jenc('\u30c6\u30b9\u30c8') + b'@Y/' + jenc('\u9078\u624b\u540d') + b'\n\x82\xa0'
    b = b'a<b ' + jenc('\u00d7\u2460') + b' <41>x' + jenc('\u5931')
    hw = bytes([0xb3, 0xdd, 0xc4, 0xde])                     # half-width katakana
    ov[0x10:0x10 + len(a)] = a
    ov[0x40:0x40 + len(b)] = b
    ov[0x60:0x60 + len(hw)] = hw
    ov[0x70:0x70 + 3] = bytes([0xda, 0xd1, 0x00])
    cont = jenc('\u4eca\u5e74\u306e')[:6]                    # 6 bytes, no NUL, followed by the next record
    ov[0x80:0x86] = cont
    ov[0x86:0x86 + 4] = jenc('\u3042\u3044')
    files = {'FLOW_PRG/T.BIN': bytes(ov)}
    ini = b'[Text]\r\n1="' + jenc('\u3053\u3093\u306b\u3061\u306f') + b'"\r\n#2="x"\r\n3="a \x22b\x22 c"\r\n'
    files['DPETC/MESSAGE.INI'] = ini
    bp = bytearray(0x40 + 2 * 92)
    bp[0x40:0x40 + 5] = jenc('\u7530\u4e2d') + b'\0'
    bp[0x40 + 92:0x40 + 92 + 3] = bytes([0xb6, 0xcf, 0x00])
    bp[0x40 + 14] = 1
    files['ETC_DATA/BPINFO.BIN'] = bytes(bp)
    headers = []
    for k, texts in enumerate([[jenc('\u306a\u308b\u307b\u3069\u3002')], [jenc('\u3042'), jenc('\u3044\u3046\u3048')]]):
        h = bytearray(2048)
        h[0:16] = b'PCM FILE START  '
        h[0x10:0x10 + 14] = b'yh\\yh_test_000' + str(k).encode()
        pos = 0x80
        for i, t in enumerate(texts):
            h[0x60 + 4 * i:0x64 + 4 * i] = pos.to_bytes(4, 'little')
            h[pos:pos + len(t)] = t
            pos += ((len(t) + 1 + 15) // 16) * 16
        headers.append(bytes(h))
    return files, headers


def rec(src, off, raw, en='', codec=None, **kw):
    codec = codec or L.codec_of(src)
    r = {'id': '%s#%x' % (src, off), 'ja': L.CODECS[codec](raw), 'en': en, 'max_bytes': kw.pop('max_bytes', 16), 'refs': kw.pop('refs', 1),
         'ctx': kw.pop('ctx', 'ptr@10')}
    r.update(kw)
    return r


class FakeDisc:
    def __init__(self, headers, lba=70000):
        self.headers, self.lba = headers, lba

    def find(self, p):
        assert p == '/BCAST/BCAST.BIN'
        return self.lba, len(self.headers) * 2048

    def read(self, lba, size):
        return self.headers[lba - self.lba][:size]

    def read_file(self, p):
        raise AssertionError('not expected')

    def close(self):
        pass


def make_workdir(tmp, files, headers, extra=None):
    """working form on disk + extracted folder; returns (tdb dir, ext dir, reader)"""
    ext = os.path.join(tmp, 'ext')
    for src, data in files.items():
        p = os.path.join(ext, *src.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(data)
    tdb = os.path.join(tmp, 'tdb')
    T, I, B = 'FLOW_PRG/T.BIN', 'DPETC/MESSAGE.INI', 'ETC_DATA/BPINFO.BIN'
    f = files[T]
    recs = [rec(T, 0x10, L.cstr(f[0x10:]), 'Test @Y/Player Name', ctx='ptr@8'),
            rec(T, 0x40, L.cstr(f[0x40:]), ''),
            rec(T, 0x60, f[0x60:0x64], 'Wtd', fmt='hwptr', ctx='hwptr ptr@0 stride-table(in-place only)', slot=8, max_bytes=12),
            rec(T, 0x70, f[0x70:0x72], 'Rem', fmt='recarr', ctx='recarray S=30 n=3 W=14 modeshare=1.00 stride-table(in-place only)', refs=None),
            rec(T, 0x80, f[0x80:0x86], 'This', fmt='gap', ctx='gap head', max_bytes=6, refs=None, cont=True),
            rec(T, 0x86, f[0x86:0x8a], 'AB', ctx='ptr@c')]
    recs[1]['skip'] = True
    recs[1]['orphan'] = True                                 # canonical order is ... orphan, skip
    write_jsonl(os.path.join(tdb, 'FLOW_PRG__T.BIN.jsonl'), recs)
    ini = files[I]
    o1 = ini.index(b'1="') + 3
    o3 = ini.index(b'3="') + 3
    irecs = [rec(I, o1, ini[o1:ini.index(b'"\r', o1)], 'Hello', max_bytes=None, refs=None, ctx='key 1'),
             rec(I, o3, b'a "b" c', '', max_bytes=None, refs=None, ctx='key 3')]
    write_jsonl(os.path.join(tdb, 'DPETC__MESSAGE.INI.jsonl'), irecs, style='spaced')
    bp = files[B]
    brecs = [rec(B, 0x40, L.cstr(bp[0x40:0x4e]), 'Tanaka', max_bytes=14, refs=None, ctx='player #0 name'),
             rec(B, 0x40 + 92, L.cstr(bp[0x40 + 92:0x40 + 106]), 'Kam', max_bytes=14, refs=None, ctx='player #1 name')]
    write_jsonl(os.path.join(tdb, 'ETC_DATA__BPINFO.BIN.jsonl'), brecs, style='spaced')
    bc = []
    for k, h in enumerate(headers):
        for o in (0x80, 0x90):
            raw = L.bcast_raw(h, o)
            if raw:
                bc.append(rec('BCAST/BCAST.BIN', k * 2048 + o, raw, 'Yes' if k else '', max_bytes=75, refs=None, ctx='clip x seg 0/1 slot 16', fmt='bcast'))
    write_jsonl(os.path.join(tdb, 'BCAST__BCAST.BIN.jsonl'), bc)
    # refit overlay of the first overlay record
    write_jsonl(os.path.join(tdb, 'refit', 'FLOW_PRG__T.BIN.jsonl'),
                [{'id': recs[0]['id'], 'ja': recs[0]['ja'], 'en': 'Player', 'why': 'test', 'cls': 'other'}], style='spaced')
    reader = L.DiscReader(FakeDisc(headers), ext)
    return tdb, ext, reader


class TestCodec(unittest.TestCase):
    def test_hash_definition(self):
        self.assertEqual(L.jah(b'abc'), hashlib.sha256(b'abc').hexdigest()[:32])
        self.assertEqual(len(L.jah(b'')), 32)
        self.assertEqual(L.jah(b''), 'e3b0c44298fc1c149afbf4c8996fb924')

    def test_codecs_roundtrip_all_bytes(self):
        rnd = random.Random(7)
        for _ in range(3000):
            b = bytes(rnd.choice([0x0a, 0x20, 0x3c, 0x41, 0x82, 0x83, 0x88, 0x9f, 0xa5, 0xdf, 0xe0, 0xea, 0x01, 0x7f, 0xff, 0x30, 0x3e, rnd.randrange(256)])
                      for _ in range(rnd.randrange(1, 12)))
            for dec in (L.decode_textdb, L.decode_common):
                self.assertEqual(L.encode_text(dec(b)), b, (dec.__name__, b))

    def test_codecs_agree_with_the_tools(self):
        import textdb
        import textfmt_common as C
        rnd = random.Random(11)
        for _ in range(3000):
            b = bytes(rnd.choice([0x0a, 0x3c, 0x41, 0x30, 0x82, 0x81, 0x83, 0x97, 0xa5, 0xdf, 0xe0, 0xea, 0x01, 0x7e, 0x40, 0x3e, 0x46, rnd.randrange(256)])
                      for _ in range(rnd.randrange(1, 10)))
            self.assertEqual(L.decode_textdb(b), textdb.decode_text(b), b)
            self.assertEqual(L.decode_common(b), C.decode_text(b), b)
            s = L.decode_common(b)
            self.assertEqual(L.encode_text(s), textdb.encode_text(s))
            self.assertEqual(L.encode_text(s), C.encode_text(s))

    def test_the_two_codecs_really_differ(self):
        raw = b'a<b ' + jenc('\u00d7')
        self.assertNotEqual(L.decode_textdb(raw), L.decode_common(raw))      # why the codec is part of the format


class TestRoundTrip(Scratch):
    def setUp(self):
        super().setUp()
        self.files, self.headers = build_fake()
        self.tdb, self.ext, self.reader = make_workdir(self.tmp, self.files, self.headers)

    def export(self, tdb=None, out=None, **kw):
        a = type('A', (), dict(tdb=tdb or self.tdb, out=out or self.path('l10n'), only=None, disc_files=None))()
        return L.cmd_export(a, SILENT)

    def do_import(self, l10n=None, out=None, **kw):
        d = dict(l10n=l10n or self.path('l10n'), out=out or self.path('back'), disc=None, extracted=None, keep_going=False, report=None,
                 max_report=200, force=False, no_verify=True, only=None, reader=self.reader)
        d.update(kw)
        msgs = []
        rc = L.cmd_import(type('A', (), d)(), msgs.append)
        return rc, msgs

    def test_round_trip_is_byte_identical(self):
        self.assertEqual(self.export(), 0)
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        names = [n for n, p, k in L.working_files(self.tdb)]
        self.assertEqual(len(names), 5)
        for n in names:
            self.assertEqual(read_bytes(os.path.join(self.tdb, *n.split('/'))), read_bytes(self.path('back', *n.split('/'))), n)

    def test_output_has_no_japanese_and_is_compact(self):
        self.assertEqual(self.export(), 0)
        for n, p, k in L.l10n_files(self.path('l10n')):
            text = read_bytes(p).decode('utf-8')
            self.assertIsNone(JP.search(text), n)
        head = json.loads(read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')[0])
        self.assertEqual(head['src'], 'FLOW_PRG/T.BIN')
        self.assertEqual(head['l10n'], 1)
        line = read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')[1]
        o = json.loads(line)
        self.assertEqual(sorted(o), ['ctx', 'en', 'id', 'jah', 'max_bytes', 'refs'])
        self.assertEqual(o['id'], '10')
        self.assertEqual(len(o['jah']), 32)

    def test_export_is_deterministic(self):
        self.export()
        self.export(out=self.path('l10n2'))
        for n, p, k in L.l10n_files(self.path('l10n')):
            self.assertEqual(read_bytes(p), read_bytes(self.path('l10n2', *n.split('/'))))

    def test_untranslated_and_identity_records(self):
        # en == ja is stored as `same`, en == '' is omitted
        p = os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')
        recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
        recs[0]['en'] = recs[0]['ja']
        recs[5]['en'] = ''
        write_jsonl(p, recs)
        self.assertEqual(self.export(), 0)
        lines = read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')
        o0, o5 = json.loads(lines[1]), json.loads(lines[6])
        self.assertTrue(o0.get('same'))
        self.assertNotIn('en', o0)
        self.assertNotIn('en', o5)
        self.assertIsNone(JP.search('\n'.join(lines)))
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        self.assertEqual(read_bytes(p), read_bytes(self.path('back', 'FLOW_PRG__T.BIN.jsonl')))

    def test_key_order_missing_keys_and_mixed_styles_survive(self):
        p = os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')
        recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
        r1 = recs[1]
        recs[1] = {k: r1[k] for k in ('id', 'ja', 'en', 'max_bytes', 'refs', 'ctx', 'skip', 'orphan')}     # not the canonical order
        del recs[2]['refs']                                                                              # a main record without refs
        recs[3] = {k: v for k, v in recs[3].items() if k != 'en'}                                        # without en
        recs[4]['extra'] = [1, 2]                                                                        # an unknown key
        os.makedirs(os.path.dirname(p), exist_ok=True)
        lines = []
        for k, r in enumerate(recs):
            lines.append(json.dumps(r, ensure_ascii=False, separators=L.STYLES['spaced' if k == 3 else 'compact']))
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        self.assertEqual(self.export(), 0)
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        self.assertEqual(read_bytes(p), read_bytes(self.path('back', 'FLOW_PRG__T.BIN.jsonl')))

    def test_no_final_newline_and_ctx_dictionary(self):
        p = os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')
        recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
        for r in recs:
            r['ctx'] = 'recarray S=30 n=5321 W=16 modeshare=0.99 stride-table(in-place only)'
        write_jsonl(p, recs, final_nl=False)
        self.assertEqual(self.export(), 0)
        head = json.loads(read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')[0])
        self.assertEqual(head['ctx'], ['recarray S=30 n=5321 W=16 modeshare=0.99 stride-table(in-place only)'])
        self.assertFalse(head['final_newline'])
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        self.assertEqual(read_bytes(p), read_bytes(self.path('back', 'FLOW_PRG__T.BIN.jsonl')))

    def test_two_sources_in_one_file_keep_full_ids(self):
        p = os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')
        recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
        raw = L.cstr(self.files['DPETC/MESSAGE.INI'][3:])
        recs.append(rec('DPETC/MESSAGE.INI', 9, b'', ''))                     # source with an empty string at offset 9? (offset 9 is inside the file)
        write_jsonl(p, recs)
        self.assertEqual(self.export(), 0)
        head = json.loads(read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')[0])
        self.assertNotIn('src', head)
        self.assertIn('#', json.loads(read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')[1])['id'])

    # ---- the safety rules
    def test_export_refuses_japanese_anywhere_else(self):
        for key, val in (('en', 'caf\u00e9 \u3042'), ('ctx', '\u30c6\u30b9\u30c8'), ('why', '\u65e5\u672c')):
            tdb = self.path('tdb_' + key)
            shutil.copytree(self.tdb, tdb)
            p = os.path.join(tdb, 'FLOW_PRG__T.BIN.jsonl')
            recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
            recs[0][key] = val
            write_jsonl(p, recs)
            out = self.path('out_' + key)
            self.assertEqual(self.export(tdb=tdb, out=out), 1, key)
            self.assertFalse(os.path.exists(out), 'nothing may be written when the export fails (%s)' % key)

    def test_leak_regex_covers_cjk_compat_blocks_but_not_plain_symbols(self):
        # cp932 characters outside kana / kanji blocks (enclosed CJK, CJK compatibility, radicals, full-width forms)
        for cp in (0x3231, 0x334c, 0x3220, 0x2f00, 0x2e80, 0xff21, 0xff71, 0xac00, 0x20000, 0x30a2, 0x7e8a):
            self.assertTrue(L.JP_RE.search(chr(cp)), hex(cp))
        for cp in (0x41, 0xe9, 0xd7, 0x2605, 0x25a0, 0x203b, 0x2019):         # English text and typographic symbols stay allowed
            self.assertFalse(L.JP_RE.search(chr(cp)), hex(cp))

    def test_hash_mismatch_is_reported_by_id_and_nothing_is_written(self):
        self.export()
        p = self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')
        lines = read_bytes(p).decode().split('\n')
        o = json.loads(lines[3])
        o['jah'] = '0' * 32
        lines[3] = json.dumps(o, separators=(',', ':'))
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
        rc, msgs = self.do_import()
        self.assertEqual(rc, 1)
        text = '\n'.join(msgs)
        self.assertIn('MISMATCH FLOW_PRG__T.BIN.jsonl  FLOW_PRG/T.BIN#%s' % o['id'], text)
        self.assertIn('hash mismatch', text)
        self.assertIn('SUMMARY', text)
        self.assertFalse(os.path.exists(self.path('back', 'FLOW_PRG__T.BIN.jsonl')), 'a file with a mismatch is not written')

    def test_keep_going_lists_all_files_and_default_stops(self):
        self.export()
        for name in ('FLOW_PRG__T.BIN.jsonl', 'DPETC__MESSAGE.INI.jsonl'):
            p = self.path('l10n', name)
            lines = read_bytes(p).decode().split('\n')
            o = json.loads(lines[1])
            o['jah'] = 'f' * 32
            lines[1] = json.dumps(o, separators=(',', ':'))
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(lines))
        rc, msgs = self.do_import(keep_going=True, out=self.path('back_k'))
        self.assertEqual(rc, 1)
        self.assertEqual(sum(1 for m in msgs if m.startswith('MISMATCH') and 'refit' not in m), 2)   # (the refit overlay of the bad file follows)
        self.assertTrue(os.path.exists(self.path('back_k', 'BCAST__BCAST.BIN.jsonl')), 'good files are still written with --keep-going')
        rc, msgs = self.do_import(out=self.path('back_s'))
        self.assertEqual(rc, 1)
        self.assertEqual(sum(1 for m in msgs if m.startswith('MISMATCH')), 1, 'without --keep-going the run stops at the first bad file')

    def test_changed_disc_bytes_are_detected(self):
        self.export()
        p = os.path.join(self.ext, 'FLOW_PRG', 'T.BIN')
        d = bytearray(read_bytes(p))
        d[0x40] ^= 1                                           # another game revision
        with open(p, 'wb') as f:
            f.write(d)
        self.reader = L.DiscReader(FakeDisc(self.headers), self.ext)
        rc, msgs = self.do_import()
        self.assertEqual(rc, 1)
        self.assertIn('FLOW_PRG/T.BIN#40', '\n'.join(msgs))

    def test_missing_offset_and_bad_bcast_segment(self):
        self.export()
        p = self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')
        lines = read_bytes(p).decode().split('\n')
        o = json.loads(lines[1])
        o['id'] = 'ffff'
        lines[1] = json.dumps(o, separators=(',', ':'))
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
        rc, msgs = self.do_import(keep_going=True)
        self.assertEqual(rc, 1)
        self.assertIn('unreadable', '\n'.join(msgs))
        self.assertIn('past the end', '\n'.join(msgs))

    def test_refit_follows_the_main_record(self):
        self.export()
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        p = self.path('l10n', 'refit', 'FLOW_PRG__T.BIN.jsonl')
        lines = read_bytes(p).decode().split('\n')
        o = json.loads(lines[1])
        self.assertNotIn('ja', o)
        o['jah'] = '1' * 32
        lines[1] = json.dumps(o, separators=(',', ':'))
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
        rc, msgs = self.do_import(out=self.path('back2'), keep_going=True)
        self.assertEqual(rc, 1)
        self.assertIn('refit', '\n'.join(msgs))

    def test_existing_output_is_not_overwritten_without_force(self):
        self.export()
        self.do_import()
        p = self.path('back', 'FLOW_PRG__T.BIN.jsonl')
        with open(p, 'ab') as f:
            f.write(b'')                                       # identical -> unchanged
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0)
        with open(p, 'wb') as f:
            f.write(b'local edit\n')
        rc, msgs = self.do_import()
        self.assertEqual(rc, 1)
        self.assertIn('REFUSED', '\n'.join(msgs))
        self.assertEqual(read_bytes(p), b'local edit\n')
        rc, msgs = self.do_import(force=True)
        self.assertEqual(rc, 0)
        self.assertEqual(read_bytes(p), read_bytes(os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')))

    def test_truncated_l10n_file_is_refused(self):
        self.export()
        p = self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')
        lines = read_bytes(p).decode().split('\n')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines[:-3]) + '\n')
        with self.assertRaises(L.L10nError):
            self.do_import()

    def test_a_file_missing_from_l10n_is_refused(self):
        self.export()
        rc, msgs = self.do_import(no_verify=False, out=self.path('back_ok'))
        self.assertEqual(rc, 0, msgs)
        os.remove(self.path('l10n', 'DPETC__MESSAGE.INI.jsonl'))          # incomplete checkout: the manifest still lists it
        with self.assertRaises(L.L10nError) as cm:
            self.do_import(no_verify=False, out=self.path('back_partial'))
        self.assertIn('DPETC__MESSAGE.INI.jsonl', str(cm.exception))
        self.assertFalse(os.path.exists(self.path('back_partial')))

    def test_identical_japanese_strings_stay_separate(self):
        # two records with the same Japanese but different places and English: key = id, the hash only verifies
        T = 'FLOW_PRG/T.BIN'
        data = bytearray(self.files[T])
        data[0xa0:0xa0 + 4] = jenc('\u306f\u3044') + b'\0\0'
        data[0xb0:0xb0 + 4] = jenc('\u306f\u3044') + b'\0\0'
        self.files[T] = bytes(data)
        with open(os.path.join(self.ext, 'FLOW_PRG', 'T.BIN'), 'wb') as f:
            f.write(data)
        p = os.path.join(self.tdb, 'FLOW_PRG__T.BIN.jsonl')
        recs = [json.loads(l) for l in read_bytes(p).decode('utf-8').split('\n') if l]
        recs.append(rec(T, 0xa0, jenc('\u306f\u3044'), 'Yes'))
        recs.append(rec(T, 0xb0, jenc('\u306f\u3044'), 'OK'))
        write_jsonl(p, recs)
        self.assertEqual(self.export(), 0)
        lines = read_bytes(self.path('l10n', 'FLOW_PRG__T.BIN.jsonl')).decode().split('\n')
        a, b = json.loads(lines[-3]), json.loads(lines[-2])
        self.assertEqual(a['jah'], b['jah'])
        self.assertNotEqual((a['id'], a['en']), (b['id'], b['en']))
        self.reader = L.DiscReader(FakeDisc(self.headers), self.ext)
        rc, msgs = self.do_import()
        self.assertEqual(rc, 0, msgs)
        self.assertEqual(read_bytes(p), read_bytes(self.path('back', 'FLOW_PRG__T.BIN.jsonl')))

    def test_manifest_records_the_disc_hashes(self):
        self.export()
        man = json.loads(read_bytes(self.path('l10n', 'MANIFEST.json')).decode('utf-8'))
        exp, rel = V.load_expected()
        self.assertEqual(man['l10n_format'], 1)
        self.assertEqual(man['hash']['truncate_bytes'], 16)
        self.assertEqual(man['hash']['algorithm'], 'sha256')
        self.assertEqual(man['disc']['track5']['sha256'], exp['track5']['sha256'])
        self.assertEqual(man['disc']['volume_iso']['sha256'], exp['volume_iso']['sha256'])
        self.assertEqual(man['game']['product'], 'HDR-0183')
        self.assertEqual(set(man['files']), {n for n, p, k in L.l10n_files(self.path('l10n'))})
        L.check_manifest(self.path('l10n'))
        man['disc']['track5']['sha256'] = '0' * 64
        with open(self.path('l10n', 'MANIFEST.json'), 'w', encoding='utf-8') as f:
            json.dump(man, f)
        with self.assertRaises(L.L10nError):
            L.check_manifest(self.path('l10n'))


class TestRawRules(unittest.TestCase):
    def test_bcast_segments(self):
        files, headers = build_fake()
        h = headers[1]
        self.assertEqual(L.bcast_raw(h, 0x80), jenc('\u3042'))
        self.assertEqual(L.bcast_raw(h, 0x90), jenc('\u3044\u3046\u3048'))
        self.assertIsNone(L.bcast_raw(h, 0x88))
        self.assertIsNone(L.bcast_raw(b'x' * 2048, 0x80))

    def test_ini_value(self):
        d = b'1="a"\r\n2="b "q" c"\r\n3="no end\r\n'
        self.assertEqual(L.ini_raw(d, 3), b'a')
        self.assertEqual(L.ini_raw(d, d.index(b'2="') + 3), b'b "q" c')
        self.assertIsNone(L.ini_raw(d, d.index(b'3="') + 3))


class TestVerifySourceDisc(Scratch):
    def test_expected_hashes_load(self):
        exp, rel = V.load_expected()
        self.assertEqual(sorted(exp), ['track1', 'track2', 'track3', 'track4', 'track5', 'volume_iso'])
        self.assertEqual(rel.get('product'), 'HDR-0183')

    def test_extracted_folder_check(self):
        ext = self.path('ext')
        os.makedirs(os.path.join(ext, 'A'))
        data = {'A/X.BIN': b'hello', 'Y.BIN': b'world'}
        rows = [(V.IP_PATH, 45000, 3, hashlib.sha256(b'ip!').hexdigest())]
        for p, d in data.items():
            with open(os.path.join(ext, *p.split('/')), 'wb') as f:
                f.write(d)
            rows.append(('/' + p, 1, len(d), hashlib.sha256(d).hexdigest()))
        with open(os.path.join(ext, 'IP.BIN'), 'wb') as f:
            f.write(b'ip!')
        rows.append((V.BCAST_PATH, 2, 99, 'a' * 64))
        man = self.path('man.tsv')
        with open(man, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# c\npath\tlba\tsize\tsha256\n' + ''.join('%s\t%d\t%d\t%s\n' % r for r in rows))
        self.assertTrue(V.verify_extracted(ext, man, log=SILENT).ok)
        with open(os.path.join(ext, 'Y.BIN'), 'wb') as f:
            f.write(b'WORLD')
        r = V.verify_extracted(ext, man, log=SILENT)
        self.assertFalse(r.ok)
        self.assertIn('/Y.BIN', r.text())
        os.remove(os.path.join(ext, 'A', 'X.BIN'))
        r = V.verify_extracted(ext, man, log=SILENT)
        self.assertIn('missing: /A/X.BIN', r.text())

    def test_hash_file_and_diff_text(self):
        p = self.path('f.bin')
        with open(p, 'wb') as f:
            f.write(b'abc')
        h = V.hash_file(p)
        self.assertEqual(h['sha1'], hashlib.sha1(b'abc').hexdigest())
        self.assertEqual(h['size'], 3)
        self.assertFalse(V.same(h, {'size': 3, 'sha1': 'x', 'sha256': h['sha256']}))
        self.assertIn('SHA-1', V.diff_text('track 1', h, {'size': 4, 'sha1': 'x', 'sha256': h['sha256']}))

    def test_a_wrong_disc_is_refused(self):
        # a volume-iso sized file that is not the game: sniff() refuses it, verify says why (no traceback)
        p = self.path('x.iso')
        with open(p, 'wb') as f:
            f.write(b'\0' * 4096)
        with self.assertRaises(V.VerifyError):
            V.verify_disc(p, log=SILENT)

    def test_a_non_matching_volume_iso_is_not_verified(self):
        p = self.path('fake.iso')
        with open(p, 'wb') as f:
            f.write(b'SEGA SEGAKATANA ' + b'\0' * (16 * 2048 - 16) + b'\x01CD001\x01' + b'\0' * (2048 - 7) + b'\0' * 2048)
        res = V.verify_disc(p, log=SILENT)
        self.assertFalse(res.ok)
        self.assertIn('NOT VERIFIED', res.text())
        self.assertIn('size', res.text())


@unittest.skipUnless(HAVE_REAL, 'needs extracted/ and the disc in the repo root')
class TestRealData(Scratch):
    """a few real working files: export -> import from extracted/ and from the disc itself"""

    def copy_working(self, names, limit=None):
        tdb = self.path('tdb')
        os.makedirs(tdb)
        for n in names:
            src = os.path.join(ROOT, 'translation', n)
            if not os.path.isfile(src):
                self.skipTest('translation/%s is not in this tree' % n)
            if limit:
                with open(src, encoding='utf-8') as f, open(os.path.join(tdb, n), 'w', encoding='utf-8', newline='\n') as g:
                    for i, line in enumerate(f):
                        if i >= limit:
                            break
                        g.write(line)
            else:
                shutil.copyfile(src, os.path.join(tdb, n))
        return tdb

    def run_rt(self, names, limit, use_disc):
        tdb = self.copy_working(names, limit)
        a = type('A', (), dict(tdb=tdb, out=self.path('l10n'), only=None, disc_files=None))()
        self.assertEqual(L.cmd_export(a, SILENT), 0)
        for n, p, k in L.l10n_files(self.path('l10n')):
            self.assertIsNone(JP.search(read_bytes(p).decode('utf-8')))
        disc = V.SourceDisc(CUE) if use_disc else None
        try:
            d = dict(l10n=self.path('l10n'), out=self.path('back'), disc=None, extracted=None if use_disc else EXTRACTED, keep_going=True,
                     report=None, max_report=20, force=False, no_verify=True, only=None,
                     reader=L.DiscReader(disc, None if use_disc else EXTRACTED))
            msgs = []
            rc = L.cmd_import(type('A', (), d)(), msgs.append)
        finally:
            if disc:
                disc.close()
        self.assertEqual(rc, 0, msgs[:5])
        for n in names:
            self.assertEqual(read_bytes(os.path.join(tdb, n)), read_bytes(self.path('back', n)), n)

    def test_overlay_ini_bpinfo_ptrblob_from_extracted(self):
        self.run_rt(['FLOW_PRG__COMM.BIN.jsonl', 'DPETC__MESSAGE.INI.jsonl', 'ETC_DATA__BPINFO.BIN.jsonl', 'ROOT__2_DP.BIN.jsonl',
                     'ROOT__1ST_READ.BIN.jsonl', 'ATFIRST__HELP.BIN.jsonl'], None, False)

    def test_everything_straight_from_the_disc_incl_bcast(self):
        self.run_rt(['FLOW_PRG__NENREP.BIN.jsonl', 'BCAST__BCAST.BIN.jsonl', 'DPETC__MESSAGE.INI.jsonl'], 3000, True)

    def test_the_disc_reader_agrees_with_extracted(self):
        d = V.SourceDisc(CUE)
        try:
            for p in ('/FLOW_PRG/COMM.BIN', '/DPETC/MESSAGE.INI', '/2_DP.BIN'):
                self.assertEqual(d.read_file(p), read_bytes(os.path.join(EXTRACTED, *p.lstrip('/').split('/'))), p)
        finally:
            d.close()

    def test_extracted_folder_matches_the_manifest(self):
        if not os.path.isfile(V.MANIFEST):
            self.skipTest('no l10n/disc-files.tsv yet')
        self.assertTrue(V.verify_extracted(EXTRACTED, log=SILENT).ok)


@unittest.skipUnless(HAVE_REAL and FULL, 'run with --full (whole tree, needs the disc)')
class TestFullTree(Scratch):
    def test_whole_tree_round_trip(self):
        out = []
        a = type('A', (), dict(tdb=os.path.join(ROOT, 'translation'), work=self.path('rt'), disc=CUE, extracted=EXTRACTED, full=True,
                               no_verify=False, any_work=False, only=None))()
        rc = L.cmd_verify(a, out.append)
        text = '\n'.join(out)
        self.assertEqual(rc, 0, text[-2000:])
        self.assertIn('PASS', text)
        self.assertIn('IDENTICAL', text)
        self.assertIn('CLEAN', text)


class TestSetup(Scratch):
    def test_texture_step_contract(self):
        # no delta folder -> nothing to do (0); a texdelta.apply_all(delta_dir, extracted_dir, out_dir) is called with exactly those
        l10n = self.path('l10n')
        os.makedirs(l10n)
        self.assertEqual(S.apply_textures(l10n, self.path('ext'), self.path('tr'), SILENT), 0)
        os.makedirs(os.path.join(l10n, 'textures'))
        calls = []
        import types
        fake = types.ModuleType('texdelta')
        fake.apply_all = lambda *a, **k: calls.append((a, k)) or 3
        old = sys.modules.get('texdelta')
        sys.modules['texdelta'] = fake
        try:
            self.assertEqual(S.apply_textures(l10n, self.path('ext'), self.path('tr'), SILENT), 0)
        finally:
            if old is not None:
                sys.modules['texdelta'] = old
            else:
                del sys.modules['texdelta']
        self.assertEqual(calls[0][0], (os.path.join(l10n, 'textures'), self.path('ext'), os.path.join(self.path('tr'), 'textures')))


if __name__ == '__main__':
    unittest.main(verbosity=1)
