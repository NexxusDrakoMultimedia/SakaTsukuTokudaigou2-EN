"""Self-test for tools/uncovered.py, tools/textfmt_recarray.py, tools/textfmt_hwkana.py and the build_patch.do_extra stage.

    python -I -X utf8 tools/test_uncovered.py

1. synthetic images: a record array with stat-preceded fields, a half-width-katakana pointer table, a text-less noise image
2. real overlays: the table records the playtest found Japanese (HOMETOWN municipality 青ヶ島村, EVENT manager 織田 道三,
   AUTOSAVE club names ｻﾘｰﾚ / ﾐｭｰﾄｽ) are extracted with the measured slot widths; en = ja is the identity for every extra
   record of every overlay in translation/; a longer English text is refused; a mutation changes only bytes inside slots
3. build_patch.build_patches on a scratch database: the English reaches the patched file, over-long English FAILS, stale ja SKIPS
4. uncovered.scan / covered_fraction on bytes
"""
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textdb as T            # noqa: E402
import textfmt_common as C    # noqa: E402
import textfmt_recarray as R  # noqa: E402
import textfmt_hwkana as H    # noqa: E402
import uncovered as U         # noqa: E402

ROOT = os.path.dirname(HERE)
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print('FAIL:', msg)


# ------------------------------------------------------------------ 1. synthetic
def synth_array():
    names = ['山田 太郎', '佐藤 次郎', '鈴木 三郎', '高橋 四郎', '田中 五郎', '伊藤 六郎', '渡辺 七郎', '中村 八郎',
             '小林 九郎', '加藤 十郎', '吉田 一', '山本 二', '松本 三', '井上 四', '木村 五', '林 六郎']
    S, W, OFF = 40, 14, 10
    buf = bytearray(b'\x00' * 64)
    for i, nm in enumerate(names):
        rec = bytearray(S)
        for k in range(OFF):
            rec[k] = 0x05 + (i + k) % 9              # stat bytes (never 0, never printable)
        raw = nm.encode('cp932')
        rec[OFF:OFF + len(raw)] = raw
        rec[OFF + W:OFF + W + 4] = bytes([0x11 + i % 5, 0x22, 0x33, 0x44])   # next field starts non-zero
        for k in range(OFF + W + 4, S):
            rec[k] = 0x07
        buf += rec
    buf += b'\x00' * 64
    return bytes(buf), names, S, W, 64 + OFF


def test_synthetic():
    data, names, S, W, first = synth_array()
    arrs = R.find_arrays(data)
    check(len(arrs) == 1, 'synthetic: one array expected, got %r' % arrs)
    if not arrs:
        return
    a = arrs[0]
    check(a.stride == S and a.width == W and len(a.members) == len(names), 'synthetic array parameters %r' % a)
    check([o for o, _ in a.members] == [first + i * S for i in range(len(names))], 'synthetic offsets')
    recs = R.extract(data, 'X/Y.BIN')
    check([r['ja'] for r in recs] == names and all(r['max_bytes'] == W for r in recs), 'synthetic records')
    check(R.apply(data, [dict(r, en=r['ja']) for r in recs]) == data, 'synthetic en=ja identity')
    new = R.apply(data, [dict(recs[0], en='Taro Yamada')])
    diff = [i for i in range(len(data)) if data[i] != new[i]]
    check(diff and min(diff) >= first and max(diff) < first + W, 'synthetic mutation only inside the slot')
    check(new[first:first + 12] == b'Taro Yamada\x00' + b'\x00' * 0 or new[first:first + 12] == b'Taro Yamada\x00', 'synthetic text written')
    try:
        R.apply(data, [dict(recs[0], en='X' * W)])
        check(False, 'synthetic over-long English must be refused')
    except ValueError:
        pass
    try:
        R.apply(data, [dict(recs[1], ja='別人 名前', en='X')])
        check(False, 'synthetic stale ja must be refused')
    except ValueError:
        pass
    # exclusion by an existing record
    ex = [(first, first + W)]
    recs2 = R.extract(data, 'X/Y.BIN', ex)
    check(len(recs2) == len(names) - 1, 'synthetic exclude')


def synth_hw():
    base = 0x8C100000
    words = ['ﾐｭｰﾄｽ', 'ｻﾘｰﾚ', 'ﾚﾝﾃﾞｨﾙ', 'ｽﾌｨｰﾀﾞ', 'ｼｭﾄﾙﾂ', 'ﾃｨｸﾞﾚ']
    img = bytearray(b'\x00' * 0x100)
    offs = []
    for w in words:
        while len(img) % 4:
            img.append(0)
        offs.append(len(img))
        img += w.encode('cp932') + b'\x00'
    while len(img) % 4:
        img.append(0)
    tbl = len(img)
    for o in offs:
        img += struct.pack('<I', base + o)
    img += b'\x00' * 16
    return bytes(img), base, words, offs, tbl


def test_hw_synthetic():
    data, base, words, offs, tbl = synth_hw()
    recs = H.extract(data, base, 'X/Z.BIN')
    check([r['ja'] for r in recs] == words, 'hw synthetic strings: %r' % [r['ja'] for r in recs])
    check(all('tbl@' in r['ctx'] for r in recs), 'hw synthetic ctx')
    check(H.apply(data, [dict(r, en=r['ja']) for r in recs]) == data, 'hw en=ja identity')
    r = recs[0]
    new = H.apply(data, [dict(r, en='Mythos')])
    check(new[offs[0]:offs[0] + 7] == b'Mythos\x00', 'hw text written')
    try:
        H.apply(data, [dict(r, en='X' * r['max_bytes'])])
        check(False, 'hw over-long English must be refused')
    except ValueError:
        pass
    # a lone candidate that is not in a table and shorter than SOLO_KANA is not accepted
    d2 = bytearray(data)
    d2[0x40:0x44] = b'\x00' + 'ｱｲ'.encode('cp932') + b'\x00'
    d2 += struct.pack('<I', base + 0x41)
    check(all(rr['ja'] != 'ｱｲ' for rr in H.extract(bytes(d2), base, 'X/Z.BIN')), 'hw lone short string must not be accepted')


# ------------------------------------------------------------------ 2. real files
def by_ja(recs, ja):
    return [r for r in recs if r['ja'] == ja]


def test_real():
    for src, ja, fmt, width in (('FLOW_PRG/HOMETOWN.BIN', '青ヶ島村', 'recarr', 35),
                                ('FLOW_PRG/EVENT.BIN', '織田 道三', 'recarr', 14),
                                ('FLOW_PRG/AUTOSAVE.BIN', 'ｻﾘｰﾚ', 'hwptr', 8),
                                ('FLOW_PRG/AUTOSAVE.BIN', 'ﾐｭｰﾄｽ', 'hwptr', 8),
                                ('FLOW_PRG/EVENT.BIN', 'ﾋﾞﾗｶｽ', 'recarr', 14)):
        img = T.load_image(src)
        strs, ptrs, _ = T.extract_image(img)
        extra = T.extra_records(img, strs)
        hit = by_ja(extra, ja)
        check(len(hit) >= 1 and hit[0]['fmt'] == fmt and hit[0]['max_bytes'] == width,
              '%s %s: expected fmt=%s slot=%d, got %r' % (src, ja, fmt, width, [(h['fmt'], h['max_bytes']) for h in hit]))
        if hit:
            off = T._off(hit[0])
            check(img.data[off:off + len(C.encode_text(ja)) + 1] == C.encode_text(ja) + b'\0', '%s %s bytes at id offset' % (src, ja))
    # en = ja identity for every extra record in the database
    n = 0
    for source, path in T.list_sources():
        jp = os.path.join(ROOT, 'translation', T.jsonl_name(source))
        if source == '1ST_READ.BIN' or not os.path.exists(jp):
            continue
        recs = [r for r in T.read_jsonl(jp) if r.get('fmt') in T.EXTRA_FMTS]
        if not recs:
            continue
        data = open(path, 'rb').read()
        for fmt, mod in (('hwptr', H), ('recarr', R)):
            sel = [dict(r, en=r['ja']) for r in recs if r['fmt'] == fmt]
            if sel:
                check(mod.apply(data, sel) == data, 'en=ja identity %s %s' % (source, fmt))
                n += len(sel)
    print('real: en=ja identity over %d extra records' % n)


# ------------------------------------------------------------------ 3. build_patch
def notex(td):
    """an empty texture directory inside the scratch database: the shared texture art is not part of these tests"""
    d = os.path.join(td, 'notex')
    os.makedirs(d, exist_ok=True)
    return d


def test_build_patch():
    import build_patch as B
    src = 'FLOW_PRG/EVENT.BIN'
    img = T.load_image(src)
    strs, ptrs, _ = T.extract_image(img)
    extra = T.extra_records(img, strs)
    pick = {'recarr': by_ja(extra, '織田 道三')[0], 'hw': by_ja(extra, 'ﾏｲﾁｰﾑ')[0]}
    recs = [dict(pick['recarr'], en='M. Oda'), dict(pick['hw'], en='My Team')]
    too_long = dict(by_ja(extra, '末吉 光')[0], en='Y' * 40)
    stale = dict(by_ja(extra, '奥村 辰彦')[0], ja='別の 人', en='Z')
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'FLOW_PRG__EVENT.BIN.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
            for r in recs + [too_long, stale]:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        res = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td))      # scratch dir: the shared texture art is not part of this test
    iso = '/' + src
    check(iso in res.patches, 'build_patches: EVENT.BIN not changed')
    if iso in res.patches:
        new = res.patches[iso]
        o1, o2 = T._off(pick['recarr']), T._off(pick['hw'])
        check(new[o1:o1 + 7] == b'M. Oda\0', 'build_patches: manager name written')
        check(new[o2:o2 + 8] == b'My Team\0', 'build_patches: hw string written')
        changed = [i for i in range(len(img.data)) if img.data[i] != new[i]]
        okspan = [(o1, o1 + pick['recarr']['max_bytes']), (o2, o2 + pick['hw']['max_bytes'])]
        check(all(any(a <= i < b for a, b in okspan) for i in changed), 'build_patches: bytes changed outside the slots')
    rep = [f for f in res.files if f.iso == iso]
    check(rep and len(rep[0].failed) == 1 and len(rep[0].skipped) == 1, 'build_patches: expected 1 failed (too long) + 1 skipped (stale): %r' %
          [(len(f.failed), len(f.skipped)) for f in rep])


# ------------------------------------------------------------------ 4. uncovered
def test_uncovered():
    d = b'\x00' * 4 + 'サリーレ'.encode('cp932') + b'\x00\x00\x00\x00' + 'ﾐｭｰﾄｽ'.encode('cp932') + b'\x00\x00' + \
        b'\x05\x06' + '織田 道三'.encode('cp932') + b'\x00' + b'\x01' + '青ヶ島村'.encode('cp932') + b'\x00' + b'\x00' * 3
    runs = U.scan(d, 2)
    got = {(c, t) for _, _, c, t in runs}
    check(('kana', 'サリーレ') in got, 'scan: kana run %r' % got)
    check(('name', '織田 道三') in got, 'scan: name run %r' % got)
    check(('kanji*', '青ヶ島村') in got or ('kana*', '青ヶ島村') in got, 'scan: stat-preceded kanji run %r' % got)
    check(U.covered_fraction([(10, 20)], 12, 18) == 1.0 and U.covered_fraction([(10, 20)], 18, 28) == 0.2 and
          U.covered_fraction([], 0, 5) == 0.0, 'covered_fraction')


def main():
    test_synthetic()
    test_hw_synthetic()
    test_real()
    test_build_patch()
    test_uncovered()
    print('test_uncovered: %s' % ('%d FAILURES' % len(fails) if fails else 'all passed'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
