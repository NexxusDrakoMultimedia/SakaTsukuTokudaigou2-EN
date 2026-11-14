"""Self-test of the half-width relocation guard (tools/hwguard.py, textfmt_hwkana.apply_relocate guard=True, translation/hw_inplace.tsv,
tools/re/s8gf_scan.py; docs/hw-relocation.md section 6).

    python -I -X utf8 tools/test_hwguard.py

1. synthetic image: code that loads a string pointer and only passes it to a call (text), code that multiplies / adds an index to the pointer
   (table base), a table of string pointers, a lone pointer field -> site_report / site_verdict
2. apply_relocate(guard=True): the text strings move (4-byte aligned, pointer words follow), the table base and the lone field NEVER move,
   their slots are never lent, a long English for them fails with a reason and leaves the image untouched there
3. the denylist file: format errors raise, is_denied / is_relocatable honour it (also for a record that looks like text), a record on it is
   written in place and never lends its slot
4. real data: every line of translation/hw_inplace.tsv names an existing pointer-referenced hwptr record; no club-word table record is on it;
   the known table bases (SCDRF 0x37df0 Damui with its 11 literals, EVENT, SEARCH, WEEKLY, ENDING, SPF_READ, the Nuchitos byte tables) are on it;
   the file equals what tools/re/s8gf_scan.py computes now (the scan is the single source of the list)
5. real overlays: apply_relocate(guard=True, align=4) with the translation DB and refit forms on a set of overlays that hold relocated strings:
   no relocated string is on the denylist or an array base (hwguard verdict text), every relocated string starts 4-byte aligned, the table
   bases and their slots stay byte-identical to the original
"""
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 're'))
import hwguard as G            # noqa: E402
import textfmt_common as C     # noqa: E402
import textfmt_hwkana as H     # noqa: E402

ROOT = os.path.dirname(HERE)
fails = []
BASE = 0x8c000000


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print('FAIL:', msg)


def ldlit(pc, lit, reg):
    d = (lit - ((pc + 4) & ~3)) // 4
    assert 0 <= d < 256 and lit % 4 == 0
    return 0xD000 | (reg << 8) | d


S1, S2, T0, T1, T2, T3, S3, SENT = 0x100, 0x110, 0x120, 0x130, 0x140, 0x150, 0x160, 0x170
SLOT = 16
JA = {S1: 'ｱｲｳｴｵ', S2: 'ｶｷｸｹｺ', T0: 'ｻｼｽｾｿ', T1: 'ﾀﾁﾂﾃﾄ', T2: 'ﾅﾆﾇﾈﾉ', T3: 'ﾊﾋﾌﾍﾎ', S3: 'ﾏﾐﾑﾒﾓ'}


def synth():
    """code A at 0 (S1 only passed to a call), code B at 0x40 (S2 multiplied / added: a table base), pointer table at 0x80 (T0..T3),
    lone pointer field at 0xA0 (S3); 16 byte slots from 0x100; non-zero sentinel at 0x170"""
    buf = bytearray(0x200)
    ops = [(0x00, 0x4F22), (0x02, ldlit(0x02, 0x20, 1)), (0x04, 0x6413), (0x06, ldlit(0x06, 0x24, 3)), (0x08, 0x430B), (0x0A, 0x0009),
           (0x0C, 0x4F26), (0x0E, 0x000B), (0x10, 0x0009),
           (0x40, 0x4F22), (0x42, ldlit(0x42, 0x60, 1)), (0x44, 0x0317), (0x46, 0x331C), (0x48, 0x4F26), (0x4A, 0x000B), (0x4C, 0x0009)]
    for o, w in ops:
        struct.pack_into('<H', buf, o, w)
    struct.pack_into('<I', buf, 0x20, BASE + S1)
    struct.pack_into('<I', buf, 0x24, 0x8c010000)            # the call target: outside the image
    struct.pack_into('<I', buf, 0x60, BASE + S2)
    for i, t in enumerate((T0, T1, T2, T3)):
        struct.pack_into('<I', buf, 0x80 + 4 * i, BASE + t)
    struct.pack_into('<I', buf, 0xA0, BASE + S3)
    recs = []
    for o, ja in JA.items():
        raw = C.encode_text(ja)
        buf[o:o + len(raw)] = raw
        ctx = 'hwptr tbl@80[%d/4] stride-table(in-place only)' % ((o - T0) // 16) if T0 <= o <= T3 else 'hwptr ptr@%x stride-table(in-place only)' % {S1: 0x20, S2: 0x60, S3: 0xA0}[o]
        recs.append({'id': 'X/G.BIN#%x' % o, 'ja': ja, 'en': '', 'max_bytes': 40, 'slot': SLOT, 'refs': 1, 'ctx': ctx, 'fmt': 'hwptr'})
    buf[SENT:SENT + 4] = b'\x01\x02\x03\x04'
    return bytes(buf), recs


def with_en(recs, mapping):
    out = []
    for r in recs:
        r = dict(r)
        o = int(r['id'].rsplit('#', 1)[1], 16)
        r['en'] = mapping.get(o, '')
        out.append(r)
    return out


def resolve(buf, wordoff):
    t = struct.unpack_from('<I', buf, wordoff)[0] - BASE
    e = buf.index(b'\0', t)
    return bytes(buf[t:e])


def test_synthetic():
    data, recs = synth()
    ix = G.ImageIndex(data, BASE)
    v = {o: G.site_verdict(ix.site_report(o)) for o in JA}
    check(v[S1][0] == 'text' and ix.site_report(S1)[0][0] == 'lit', 'sites: S1 loaded and only passed to a call is text %r' % (v[S1],))
    check(v[S2][0] == 'base' and 'mul' in v[S2][1], 'sites: S2 with mul.l / add is a table base %r' % (v[S2],))
    check(all(v[o][0] == 'text' and ix.site_report(o)[0][0] == 'ptrtab' for o in (T0, T1, T2, T3)), 'sites: table words are text %r' % ([v[o] for o in (T0, T1)],))
    check(v[S3][0] == 'unknown' and ix.site_report(S3)[0][0] == 'field', 'sites: a lone pointer field is unknown (fail safe) %r' % (v[S3],))
    check(G.site_verdict([])[0] == 'unknown', 'sites: no pointer = unknown')
    # a window without function markers: the load is not believed, but an index use still is
    d2 = bytearray(data)
    for o in (0x00, 0x0C, 0x0E, 0x40, 0x48, 0x4A):
        struct.pack_into('<H', d2, o, 0x0009)                 # remove the markers
    ix2 = G.ImageIndex(bytes(d2), BASE)
    check(ix2.site_report(S2)[0][0] == 'litx' and G.site_verdict(ix2.site_report(S2))[0] == 'base', 'sites: an index use outside recognised code still counts')
    check(ix2.site_report(S1)[0][0] == 'ptrtab' or ix2.site_report(S1)[0][0] == 'field', 'sites: a call use outside code is just a pointer word')


def test_guard():
    data, recs = synth()
    long18 = 'A' * 17                                       # 18 bytes incl. NUL > slot 16
    en = {S1: long18, S2: 'Short', T0: long18, T1: 'b', T2: 'c', T3: 'd', S3: 'Short3'}
    r = H.apply_relocate(data, BASE, with_en(recs, en), align=4, guard=True)
    check(not r.failed and not r.skipped, 'guard: short forms of the base and the field, long text strings: no failure %r' % (r.failed,))
    moved = {i: w for i, (w, _) in r.where.items() if w == 'relocated'}
    check(len(moved) >= 2, 'guard: the long text strings moved %r' % (r.where,))
    check(resolve(r.data, 0x20) == long18.encode() and resolve(r.data, 0x80) == long18.encode(), 'guard: pointer words follow the moved strings')
    check(all(o % 4 == 0 for w, o in r.where.values() if w == 'relocated'), 'guard: relocated strings are 4-byte aligned')
    check(struct.unpack_from('<I', r.data, 0x60)[0] == BASE + S2 and r.data[S2:S2 + 6] == b'Short\0', 'guard: the table base stays, English written in place')
    check(struct.unpack_from('<I', r.data, 0xA0)[0] == BASE + S3 and r.data[S3:S3 + 7] == b'Short3\0', 'guard: the lone field stays, English written in place')
    # nothing may be written into the slot of S2 / S3 except their own English (never lent)
    check(r.data[S2 + 6:S2 + SLOT] == b'\0' * (SLOT - 6) and r.data[S3 + 7:S3 + SLOT] == b'\0' * (SLOT - 7), 'guard: slots of base / field are not lent')
    # a long English for a base / field cannot be placed: FAILED with the reason, image untouched at that string
    en2 = dict(en)
    en2[S2], en2[S3] = long18, long18
    r2 = H.apply_relocate(data, BASE, with_en(recs, en2), align=4, guard=True)
    ids = {i: m for i, m in r2.failed}
    check(set(ids) == {recs[1]['id'], recs[6]['id']} and all('cannot be relocated' in m for m in ids.values()), 'guard: long English for base / field fails %r' % (ids,))
    check(r2.data[S2:S2 + SLOT] == data[S2:S2 + SLOT] and struct.unpack_from('<I', r2.data, 0x60)[0] == BASE + S2, 'guard: failed base keeps its bytes and pointer')
    # without the guard the field would have moved (library default: unchanged behaviour); the base too (nothing knows it)
    r3 = H.apply_relocate(data, BASE, with_en(recs, en2), align=4)
    check(not r3.failed, 'no guard: everything moves (the old behaviour) %r' % (r3.failed,))
    check(struct.unpack_from('<I', r3.data, 0x60)[0] != BASE + S2, 'no guard: the table base was moved (this is what broke prop10c)')


def test_denylist():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, 'deny.tsv')
        open(p, 'w', encoding='utf-8', newline='\n').write('# c\nX/G.BIN#120\tmanual\ttest\n\nX/G.BIN#130\tbase\t\n')
        m = G.load_deny(p)
        check(set(m) == {'X/G.BIN#120', 'X/G.BIN#130'} and m['X/G.BIN#120'] == ('manual', 'test'), 'deny: parsed %r' % (m,))
        check(G.is_denied('X/G.BIN#120', p) and not G.is_denied('X/G.BIN#140', p), 'deny: is_denied')
        for bad in ('X/G.BIN#120\n', 'X/G.BIN#120\tsure\tx\n', 'nonsense\tbase\tx\n'):
            open(p, 'w', encoding='utf-8', newline='\n').write(bad)
            os.utime(p, (os.path.getmtime(p) + 5, os.path.getmtime(p) + 5))
            try:
                G.load_deny(p)
                check(False, 'deny: malformed line %r accepted' % bad)
            except ValueError:
                pass
        check(G.load_deny(os.path.join(td, 'missing.tsv')) == {}, 'deny: a missing file is an empty list')
        # s8gkc: a GUARDED build must not run without the list (a missing file would silently lift every head / unknown / manual denial)
        try:
            G.require_deny(os.path.join(td, 'missing.tsv'))
            check(False, 'deny: require_deny accepted a missing file')
        except RuntimeError:
            pass
        open(p, 'w', encoding='utf-8', newline='\n').write('# only a comment\n')
        os.utime(p, (os.path.getmtime(p) + 9, os.path.getmtime(p) + 9))
        try:
            G.require_deny(p)
            check(False, 'deny: require_deny accepted an empty list')
        except RuntimeError:
            pass
        old = G.DENY_FILE
        G.DENY_FILE = os.path.join(td, 'missing.tsv')
        try:
            data, recs = synth()
            H.apply_relocate(data, BASE, with_en(recs, {S1: 'A' * 17}), align=4, guard=True)
            check(False, 'deny: apply_relocate(guard=True) ran without the denylist file')
        except RuntimeError:
            pass
        finally:
            G.DENY_FILE = old
        data, recs = synth()
        check(not H.apply_relocate(data, BASE, with_en(recs, {S1: 'Short'}), align=4).failed, 'deny: the unguarded library call needs no file')
    real = G.load_deny()
    check(len(real) > 100, 'deny: the real file is loaded (%d)' % len(real))
    # a record on the real list is not relocatable even though it looks like text
    rid = next(iter(real))
    fake = {'id': rid, 'fmt': 'hwptr', 'refs': 1, 'ctx': 'hwptr tbl@0[0/3] stride-table(in-place only)', 'max_bytes': 40, 'slot': 8}
    check(not H.is_relocatable(fake) and 'denied' in H.fixed_reason(fake), 'deny: is_relocatable honours the file')
    fake['id'] = 'X/NOPE.BIN#10'
    check(H.is_relocatable(fake), 'deny: an unlisted pointer-referenced record is relocatable')


def test_heads():
    """array_heads: a lone-literal record with a recarray one stride behind is a head; an entry of a pointer table (tbl@) never is (s8gkc: BACKUP
    club words Panthera / Mythos were denied because a spurious recarray sat 240 bytes behind them)"""
    def hw(off, ctx):
        return {'id': 'X/H.BIN#%x' % off, 'fmt': 'hwptr', 'refs': 1, 'ctx': ctx, 'max_bytes': 40, 'slot': 8, 'ja': '', 'en': ''}
    arr = {'id': 'X/H.BIN#%x' % (0x1000 + 56), 'fmt': 'recarr', 'ctx': 'recarray S=56 n=9 W=14 modeshare=1.00', 'max_bytes': 14}
    single, table = hw(0x1000, 'hwptr ptr@20 stride-table(in-place only)'), hw(0x2000, 'hwptr tbl@40[3/55] stride-table(in-place only)')
    arr2 = dict(arr, id='X/H.BIN#%x' % (0x2000 + 240), ctx='recarray S=240 n=9 W=14 modeshare=1.00')
    heads = G.array_heads([single, table], [arr, arr2])
    check(heads == {0x1000}, 'heads: only the lone-literal record is a head %r' % (sorted(heads),))


def load_db(source):
    p = os.path.join(ROOT, 'translation', source.replace('/', '__') + '.jsonl')
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def test_real_list():
    real = G.load_deny()
    bysrc = {}
    for rid in real:
        bysrc.setdefault(rid.rsplit('#', 1)[0], []).append(rid)
    miss = []
    for src, ids in bysrc.items():
        have = {r['id']: r for r in load_db(src)}
        for rid in ids:
            r = have.get(rid)
            if r is None or r.get('fmt') != 'hwptr' or not r.get('refs'):
                miss.append(rid)
    check(not miss, 'list: %d entries name no pointer-referenced hwptr record: %r' % (len(miss), miss[:5]))
    must = ['FLOW_PRG/SCDRF.BIN#37df0', 'FLOW_PRG/EVENT.BIN#da184', 'FLOW_PRG/SEARCH.BIN#6ae84', 'FLOW_PRG/WEEKLY.BIN#3f66c',
            'FLOW_PRG/ENDING.BIN#7532c', 'FLOW_PRG/SPF_READ.BIN#536d8']
    check('FLOW_PRG/BACKUP.BIN#3c968' not in real and 'FLOW_PRG/BACKUP.BIN#3c9e0' not in real, 'list: the BACKUP club word table entries (Panthera / Mythos) are text')
    check(all(m in real for m in must), 'list: the known Damui table bases are on it %r' % [m for m in must if m not in real])
    nu = [r for src in ('FLOW_PRG/BACKUP.BIN', 'FLOW_PRG/ABROAD.BIN', 'FLOW_PRG/BPMATCH.BIN') for r in load_db(src) if r.get('en') == 'Nuchitos']
    check(len(nu) == 3 and all(r['id'] in real for r in nu), 'list: the Nuchitos byte tables are on it')
    # club words: the 55 / 85 word tables are plain pointer tables and must stay relocatable
    club = [r for r in load_db('FLOW_PRG/DRAFT.BIN') if r.get('fmt') == 'hwptr' and 'tbl@' in (r.get('ctx') or '') and r.get('en') in ('Avalanche', 'Monolith', 'Cielo', 'Corriente')]
    check(club == [] or not any(r['id'] in real for r in club), 'list: club word table records are not denied')
    import s8gf_scan as re_scan
    cur = open(G.DENY_FILE, encoding='utf-8').read()
    rows = re_scan.classify_all()
    ncls = {}
    for r in rows:
        ncls[r['cls']] = ncls.get(r['cls'], 0) + 1
    want = {r['id'] for r in rows if r['cls'] != 'text'}
    have = {k for k, v in real.items() if v[0] != 'manual'}
    check(want == have, 'list: translation/hw_inplace.tsv differs from the scan (%d only in scan, %d only in file): rerun tools/re/s8gf_scan.py --deny' % (
        len(want - have), len(have - want)))
    check(ncls.get('text', 0) > 100000, 'list: the scan finds the string-pointer tables (%r)' % ncls)
    return rows


def test_real_overlays(rows):
    import build_patch as B
    import refit
    by_src = B.load_tdb('translation')
    B.apply_refit(by_src, 'translation', None, True)
    real = G.load_deny()
    ids_text = {r['id'] for r in rows if r['cls'] == 'text'}
    total_moved = 0
    for source in ('FLOW_PRG/SCDRF.BIN', 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/SEARCH.BIN', 'FLOW_PRG/CHALMODE.BIN', 'FLOW_PRG/DRAFT.BIN', 'FLOW_PRG/ABROAD.BIN'):
        recs = [r for r in by_src[source] if r.get('fmt') == 'hwptr' and r.get('en')]
        others = [r for r in by_src[source] if r.get('fmt') != 'hwptr']
        if not recs:
            continue
        import textdb
        img = textdb.load_image(source)
        heads = G.array_heads(recs, others)
        use = [r for r in recs if int(r['id'].rsplit('#', 1)[1], 16) not in heads]
        prot = [(int(r['id'].rsplit('#', 1)[1], 16), int(r['id'].rsplit('#', 1)[1], 16) + (r.get('max_bytes') or 0)) for r in others]
        rr = H.apply_relocate(img.data, img.base, use, share=True, protect=prot, align=B.HW_ALIGN, guard=True)
        moved = [i for i, (w, _) in rr.where.items() if w == 'relocated']
        total_moved += len(moved)
        check(not [i for i in moved if i in real or i not in ids_text], '%s: a denied / non-text record was relocated' % source)
        check(all(o % 4 == 0 for w, o in rr.where.values() if w == 'relocated'), '%s: a relocated string is not 4-byte aligned' % source)
        orig = img.data
        ixs = G.ImageIndex(orig, img.base)
        for rid in real:
            if not rid.startswith(source + '#'):
                continue
            off = int(rid.rsplit('#', 1)[1], 16)
            rec = next((r for r in recs if r['id'] == rid), None)
            if rec is None:
                continue
            slot = rec.get('slot') or rec['max_bytes']
            failed = {f for f, _ in rr.failed}
            if rid in failed or off in heads:
                want = orig[off:off + slot]                       # too long for the slot, or a head (written by the in-place path of do_extra, not by apply_relocate): untouched here
            else:
                want = C.encode_text(rec['en']).ljust(slot, b'\0')   # English in place, zero padded, nothing lent to another string
            check(rr.data[off:off + slot] == want, '%s: slot of denied %s is not (English in place + zeros)' % (source, rid))
            for w in ixs.targets.get(off, []):
                check(rr.data[w:w + 4] == orig[w:w + 4], '%s: pointer word %#x of denied %s changed' % (source, w, rid))
    check(total_moved > 0, 'real overlays: something was relocated (club words) %d' % total_moved)


def main():
    test_synthetic()
    test_guard()
    test_denylist()
    test_heads()
    rows = test_real_list()
    test_real_overlays(rows)
    print('test_hwguard: %s' % ('%d FAILURES' % len(fails) if fails else 'all passed'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
