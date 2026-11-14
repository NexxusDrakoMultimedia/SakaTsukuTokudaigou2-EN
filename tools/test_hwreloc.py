"""Self-test of the half-width pointer string relocation (tools/textfmt_hwkana.apply_relocate, build_patch --hw-relocate,
tools/re/hwr_raise_budget.py; docs/hw-relocation.md).

    python -I -X utf8 tools/test_hwreloc.py

1. synthetic pool: fits = apply() bytes; a long string moves into the pool slack, pointers follow; no room FAILS and keeps the
   Japanese; nothing outside the slots of translated records changes; determinism; share; align; stale / index-addressed /
   refs-mismatch records; overlapping slots
2. real overlays: forced identity round trip (every hwptr string of every overlay relocated with en = ja, every pointer word
   reads back the Japanese string, only slot bytes changed)
3. build_patch on a scratch database: flag off FAILS the long string (with a hint), flag on relocates it, short strings stay
4. the budget tool on a scratch copy of a jsonl (slot kept, max_bytes raised, idempotent, reversible)
"""
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 're'))
import textdb as T            # noqa: E402
import textfmt_common as C    # noqa: E402
import textfmt_hwkana as H    # noqa: E402

ROOT = os.path.dirname(HERE)
fails = []
BASE = 0x8c000000


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print('FAIL:', msg)


# ------------------------------------------------------------------ 1. synthetic
JA = ['ｱｲｳｴｵ', 'ｶｷｸｹｺ', 'ｻｼｽｾｿ', 'ﾀﾁﾂﾃﾄ', 'ﾅﾆﾇﾈﾉ', 'ﾊﾋﾌﾍﾎ', 'ﾏﾐﾑﾒﾓ', 'ﾔﾕﾖ']
TBL, POOL = 0x40, 0x100


def synth():
    """pointer table at 0x40 (8 words) -> 8 slots of 8 bytes at 0x100; a non-zero sentinel closes the pool"""
    buf = bytearray(0x200)
    recs = []
    for i, ja in enumerate(JA):
        o = POOL + 8 * i
        raw = C.encode_text(ja)
        buf[o:o + len(raw)] = raw
        struct.pack_into('<I', buf, TBL + 4 * i, BASE + o)
        recs.append({'id': 'X/T.BIN#%x' % o, 'ja': ja, 'en': '', 'max_bytes': 8, 'refs': 1,
                     'ctx': 'hwptr tbl@%x[%d/8] stride-table(in-place only)' % (TBL, i), 'fmt': 'hwptr'})
    buf[POOL + 64:POOL + 68] = b'\x01\x02\x03\x04'
    return bytes(buf), recs


def resolve(buf, wordoff):
    t = struct.unpack_from('<I', buf, wordoff)[0] - BASE
    return bytes(buf[t:buf.index(b'\0', t)])


def diff_outside(old, new, recs_slots):
    return [i for i in range(len(old)) if old[i] != new[i] and not any(a <= i < b for a, b in recs_slots)]


def with_en(recs, mapping, budget=None, slot=None):
    out = []
    for i, r in enumerate(recs):
        r = dict(r)
        if i in mapping:
            r['en'] = mapping[i]
            if budget:
                r['slot'], r['max_bytes'] = r['max_bytes'], budget
        out.append(r)
    return out


def test_synthetic():
    data, recs = synth()
    allslots = [(POOL + 8 * i, POOL + 8 * i + 8) for i in range(8)] + [(TBL, TBL + 32)]      # pool + the pointer table
    # a. everything fits: identical to apply()
    short = with_en(recs, {i: 'ab%d' % i for i in range(8)})
    r = H.apply_relocate(data, BASE, short)
    check(r.data == H.apply(data, short) and not r.failed and not r.skipped, 'fits: relocate == apply')
    check(r.stats['relocated'] == 0 and r.stats['in_place'] == 8, 'fits: nothing moved')
    # b. one long string moves into the slack of the neighbours
    mp = {i: 'ab%d' % i for i in range(8)}
    mp[3] = 'Long Club Name.'            # 15 + NUL = 16 > slot 8, budget 40
    lr = with_en(recs, mp, budget=40)
    r = H.apply_relocate(data, BASE, lr)
    check(not r.failed and not r.skipped, 'long: no failure %r' % r.failed)
    check(r.where.get(lr[3]['id'], ('', 0))[0] == 'relocated', 'long: string 3 relocated')
    for i in range(8):
        check(resolve(r.data, TBL + 4 * i) == C.encode_text(mp[i]), 'long: pointer %d resolves' % i)
    check(not diff_outside(data, r.data, allslots), 'long: only pool bytes changed')
    check(r.stats['slack'] >= 0 and r.stats['capacity'] == 64, 'long: stats %r' % r.stats)
    r2 = H.apply_relocate(data, BASE, lr)
    check(r2.data == r.data and r2.where == r.where, 'determinism')
    # c. no room: three records of 30 bytes in an arena of 24 -> all fail, Japanese kept, nothing changes
    big = with_en(recs, {1: 'A' * 29, 2: 'B' * 29, 5: 'C' * 29}, budget=40)
    r = H.apply_relocate(data, BASE, big)
    check(len(r.failed) == 3 and r.data == data, 'no room: 3 failed and the image is untouched (%d failed)' % len(r.failed))
    # c2. partial: two translated (arena 16) one of 12 fits (own slot 8 + neighbour 8), the other needs room too
    part = with_en(recs, {1: 'A' * 11, 2: 'B', 5: 'C' * 20}, budget=40)
    r = H.apply_relocate(data, BASE, part)
    check([f[0] for f in r.failed] == [part[5]['id']], 'partial: only the 20 byte string fails %r' % r.failed)
    check(resolve(r.data, TBL + 4 * 5) == C.encode_text(JA[5]), 'partial: failed string keeps its Japanese')
    check(resolve(r.data, TBL + 4 * 1) == b'A' * 11 and resolve(r.data, TBL + 4 * 2) == b'B', 'partial: others written')
    check(not diff_outside(data, r.data, [allslots[1], allslots[2], (TBL + 4, TBL + 12)]), 'partial: only slots 1 and 2 changed')
    # d. index-addressed (refs 0) and hwpool records cannot move
    nr = with_en(recs, {0: 'x' * 12}, budget=40)
    nr[0]['refs'] = 0
    r = H.apply_relocate(data, BASE, nr)
    check(len(r.failed) == 1 and 'cannot be relocated' in r.failed[0][1] and r.data == data, 'refs 0: fails %r' % r.failed)
    pl = with_en(recs, {0: 'x' * 12}, budget=40)
    pl[0]['ctx'] = 'hwpool run=7 stride-table(in-place only)'
    r = H.apply_relocate(data, BASE, pl)
    check(len(r.failed) == 1 and r.data == data, 'hwpool: fails')
    # e. stale Japanese -> skipped; budget exceeded -> failed; refs mismatch -> failed
    st = with_en(recs, {0: 'a'})
    st[0]['ja'] = 'ﾇﾇﾇ'
    r = H.apply_relocate(data, BASE, st)
    check(len(r.skipped) == 1 and not r.failed and r.data == data, 'stale: skipped')
    ob = with_en(recs, {0: 'q' * 40}, budget=40)
    r = H.apply_relocate(data, BASE, ob)
    check(len(r.failed) == 1 and 'does not fit' in r.failed[0][1], 'budget: 40 chars + NUL > 40 fails')
    rm = with_en(recs, {0: 'q' * 20, 1: 'z'}, budget=40)
    rm[0]['refs'] = 2
    r = H.apply_relocate(data, BASE, rm)
    check(len(r.failed) == 1 and 'pointer word' in r.failed[0][1], 'refs mismatch: fails')
    check(resolve(r.data, TBL + 4) == b'z', 'refs mismatch: the other record is still written')
    # f. share
    sh = with_en(recs, {1: 'S' * 14, 2: 'S' * 14}, budget=40)
    r = H.apply_relocate(data, BASE, sh, share=True)
    p1, p4 = [struct.unpack_from('<I', r.data, TBL + 4 * i)[0] for i in (1, 2)]
    check(not r.failed and p1 == p4, 'share: one copy for identical strings %r' % r.failed)
    r = H.apply_relocate(data, BASE, sh, share=False)
    check(len(r.failed) == 2 and r.data == data, 'no share: two copies need 30 bytes of a 16 byte arena: both fail, image untouched %r' % r.failed)
    # g. align
    r = H.apply_relocate(data, BASE, lr, align=4)
    check(all(v[1] % 4 == 0 for v in r.where.values() if v[0] == 'relocated'), 'align 4')
    # h. forced identity on the synthetic pool
    ident = [dict(x, en=x['ja']) for x in recs]
    r = H.apply_relocate(data, BASE, ident, force=True)
    check(not r.failed and r.stats['relocated'] == 8, 'force: all 8 relocated')
    check(all(resolve(r.data, TBL + 4 * i) == C.encode_text(JA[i]) for i in range(8)), 'force: identity round trip')
    check(not diff_outside(data, r.data, allslots), 'force: only pool bytes changed')
    # i. overlapping slots fail (never two strings on one byte)
    ov = with_en(recs, {0: 'a', 1: 'b'})
    ov[0]['max_bytes'] = 16
    r = H.apply_relocate(data, BASE, ov)
    check(len(r.failed) + len(r.skipped) >= 1, 'overlap: refused %r' % (r.failed + r.skipped))
    # j. a pointer target inside the slot is refused (stale slot width)
    d2 = bytearray(data)
    struct.pack_into('<I', d2, 0x80, BASE + POOL + 4 + 8 * 0)
    r = H.apply_relocate(bytes(d2), BASE, with_en(recs, {0: 'a'}))
    check(not r.failed and r.data == H.apply(bytes(d2), with_en(recs, {0: 'a'})), 'inner target: a fitting string is written in place as apply() does')
    r = H.apply_relocate(bytes(d2), BASE, with_en(recs, {0: 'x' * 12, 1: 'y' * 3}, budget=40))
    check(len(r.failed) == 1 and 'inside the slot' in r.failed[0][1] and resolve(r.data, TBL) == C.encode_text(JA[0]), 'inner target: relocation refused')
    # ... and its slot is not lent to other strings: record 1 (needs 12 with record 0 frozen) finds no room
    r = H.apply_relocate(bytes(d2), BASE, with_en(recs, {0: 'a', 1: 'y' * 11}, budget=40))
    check(len(r.failed) == 1 and r.failed[0][0] == recs[1]['id'] and resolve(r.data, TBL) == b'a', 'frozen slot is not lent')
    # protected range: a pointer word inside it is never rewritten
    r = H.apply_relocate(data, BASE, with_en(recs, {3: 'Long Club Name.'}, budget=40), force=False, protect=[(TBL + 12, TBL + 16)])
    check(len(r.failed) == 1 and 'protected' in r.failed[0][1] and r.data == data, 'protect: refused, image untouched')
    # k. slot_of / apply honour `slot` (raised max_bytes never widens an in-place write)
    wide = with_en(recs, {0: 'x' * 12}, budget=40)
    try:
        H.apply(data, wide)
        check(False, 'apply: 12 bytes must not fit slot 8')
    except ValueError:
        pass


# ------------------------------------------------------------------ 2. real overlays
def test_real():
    nsrc = nstr = nsuffix = 0
    for source, path in T.list_sources():
        jp = os.path.join(ROOT, 'translation', T.jsonl_name(source))
        if source == '1ST_READ.BIN' or not os.path.exists(jp):
            continue
        recs = [r for r in T.read_jsonl(jp) if r.get('fmt') == 'hwptr']
        rel = [r for r in recs if H.is_relocatable(r)]
        if not rel:
            continue
        img = T.load_image(source)
        data = img.data
        sel = [dict(r, en=r['ja']) for r in rel]
        res = H.apply_relocate(data, img.base, sel, force=True)
        # a suffix pointer into the string (`ｱｲｳ` and `ｲｳ`) forbids moving: refused safely, never corrupted
        hard = [f for f in res.failed if 'another pointer target' not in f[1]]
        check(not hard and not res.skipped, '%s: forced identity failed %r' % (source, (hard + res.skipped)[:2]))
        nsuffix += len(res.failed)
        words = H._words(data, img.base)
        bad = 0
        for r in sel:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            ja = C.encode_text(r['ja'])
            if r['id'] not in res.where:
                continue
            for w in words.get(off, []):
                t = struct.unpack_from('<I', res.data, w)[0] - img.base
                if res.data[t:t + len(ja) + 1] != ja + b'\0':
                    bad += 1
        check(bad == 0, '%s: %d pointers do not read back the original string' % (source, bad))
        slots = sorted((int(r['id'].rsplit('#', 1)[1], 16), int(r['id'].rsplit('#', 1)[1], 16) + H.slot_of(r)) for r in sel)
        import bisect
        starts = [a for a, _ in slots]
        out = 0
        pbytes = {w + k for r in sel for w in words.get(int(r['id'].rsplit('#', 1)[1], 16), []) for k in range(4)}
        for i in (j for j in range(len(data)) if data[j] != res.data[j]):
            k = bisect.bisect_right(starts, i) - 1
            if not (k >= 0 and slots[k][0] <= i < slots[k][1]):
                # a pointer word of a relocated record
                if i not in pbytes:
                    out += 1
        check(out == 0, '%s: %d bytes changed outside pool slots / pointer words' % (source, out))
        res2 = H.apply_relocate(data, img.base, sel, force=True)
        check(res2.data == res.data, '%s: not deterministic' % source)
        nsrc += 1
        nstr += len(res.where)
    print('real: forced identity round trip over %d overlays, %d strings (%d refused: inner pointer target)' % (nsrc, nstr, nsuffix))
    check(nsrc >= 60, 'real: expected >= 60 overlays with relocatable hw strings, got %d' % nsrc)


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
    extra = [r for r in T.extra_records(img, strs) if r['fmt'] == 'hwptr' and H.is_relocatable(r) and r['refs'] == 1 and r['max_bytes'] == 8]
    pick = extra[:8]
    check(len(pick) == 8, 'build: need 8 slot-8 hw records in EVENT.BIN')
    longs = 'Longest Club.'                # 13 + NUL = 14 > 8
    recs = []
    for i, r in enumerate(pick):
        r = dict(r)
        r['en'] = longs if i == 2 else 'a%d' % i
        r['slot'], r['max_bytes'] = r['max_bytes'], 40
        recs.append(r)
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'FLOW_PRG__EVENT.BIN.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        off = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td))
        on = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td), hw_relocate='on')
        on2 = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td), hw_relocate='on')
    iso = '/' + src
    roff = [f for f in off.files if f.iso == iso][0]
    ron = [f for f in on.files if f.iso == iso][0]
    check(len(roff.failed) == 1 and 'hw-relocate' in roff.failed[0][1], 'build off: the long string fails with a hint %r' % roff.failed)
    check(not ron.failed and not ron.skipped and ron.relocated >= 1, 'build on: relocated, 0 failed %r' % ron.failed)
    check(on.patches[iso] == on2.patches[iso], 'build on: deterministic')
    new = on.patches[iso]
    words = H._words(img.data, img.base)
    for i, r in enumerate(pick):
        o = T._off(r)
        for w in words[o]:
            want = longs if i == 2 else 'a%d' % i
            check(resolve_at(new, w, img.base) == want.encode('ascii'), 'build on: pointer of record %d reads %r' % (i, want))
    # flag on, nothing too long: byte-identical to flag off
    short = [dict(r, en='a%d' % i) for i, r in enumerate(recs)]
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'FLOW_PRG__EVENT.BIN.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
            for r in short:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        a = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td))
        b = B.build_patches(td, only=['EVENT.BIN'], textures_dir=notex(td), hw_relocate='on')
    check(a.patches[iso] == b.patches[iso], 'build: flag on == flag off when everything fits')


def resolve_at(buf, wordoff, base):
    t = struct.unpack_from('<I', buf, wordoff)[0] - base
    return bytes(buf[t:buf.index(b'\0', t)])


# ------------------------------------------------------------------ 4. budget tool
def test_budget_tool():
    import hwr_raise_budget as G
    with tempfile.TemporaryDirectory() as td:
        recs = [{'id': 'A/B.BIN#10', 'ja': 'ｱｲｳ', 'en': 'Abc', 'max_bytes': 8, 'refs': 1, 'ctx': 'hwptr ptr@4', 'fmt': 'hwptr'},
                {'id': 'A/B.BIN#20', 'ja': 'ｱｲｳ', 'en': '', 'max_bytes': 4, 'refs': 0, 'ctx': 'hwpool run=7 stride-table(in-place only)', 'fmt': 'hwptr'},
                {'id': 'A/B.BIN#30', 'ja': '日本', 'en': 'x', 'max_bytes': 6, 'refs': 1, 'ctx': 'ptr@8', 'fmt': 'str'},
                {'id': 'A/B.BIN#40', 'ja': 'ｱｲｳ', 'en': '', 'max_bytes': 50, 'refs': 1, 'ctx': 'hwptr ptr@c', 'fmt': 'hwptr'}]
        p = os.path.join(td, 'A__B.BIN.jsonl')
        T.write_jsonl(p, recs)
        n = G.raise_file(p, 40)
        out = T.read_jsonl(p)
        check(n == 1, 'budget: one record raised (%d)' % n)
        check(out[0]['max_bytes'] == 40 and out[0]['slot'] == 8 and list(out[0]).index('slot') == list(out[0]).index('max_bytes') + 1, 'budget: raised, slot kept next to it')
        check(out[1] == recs[1] and out[2] == recs[2], 'budget: pool / non-hwptr records untouched')
        check(out[3]['max_bytes'] == 50 and 'slot' not in out[3], 'budget: a larger max_bytes is never lowered')
        check(G.raise_file(p, 40) == 0, 'budget: idempotent')
        m = G.revert_file(p)
        back = T.read_jsonl(p)
        check(m == 1 and back == recs, 'budget: revert restores the original records')
        check(not os.path.exists(p + '.tmp'), 'budget: no temp file left')


def main():
    test_synthetic()
    test_real()
    test_build_patch()
    test_budget_tool()
    print('test_hwreloc: %s' % ('%d FAILURES' % len(fails) if fails else 'all passed'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
