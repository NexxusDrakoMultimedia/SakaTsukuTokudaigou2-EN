"""Self-test of the opt-in refit overlays (tools/refit.py, translation/refit/*.jsonl, tools/re/rfit_*.py).

    python -I -X utf8 tools/test_refit.py [--quick]

1. unit (synthetic DB + scratch overlay directory): malformed / duplicate overlay records are refused; load_overlays changes
   the `en` of the matching records ONLY (in place, returned), unknown id / stale ja / untranslated / same English are skipped;
   relocate=False skips a refit that does not fit the in-place slot of an hwptr record; a fixed field (record array, interior
   pointer) never takes more than its field; apply_overlays is copy-on-write; validate reports class caps (characters, pixel
   width), ja mismatch, encoding; everything deterministic
2. kana: tools/re/rfit_kana.hepburn on a table of known readings
3. real overlays: every record is well formed, its id exists, its ja matches, English is ASCII and differs from the DB, the
   static validation (hard caps, class caps, pixel width) passes with hw relocation on, the DB is untouched by apply_overlays,
   relocate=False yields only forms that fit in place, the known rough forms are refit where the overlay carries them
4. the REAL build code (build_patch.do_overlay / do_extra, share dup, append-safe, repack on) on every source with overlay
   records: no refit fails and no failure is added, with hw relocation on; with relocation off (overlays loaded with
   relocate=False) likewise.  --quick limits this to a handful of sources.
5. the default DB is unchanged by this module (nothing in translation/*.jsonl is modified, no overlay -> no change)
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 're'))
import refit as R             # noqa: E402
import rfit_kana as K         # noqa: E402

ROOT = os.path.dirname(HERE)
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print('FAIL:', msg)


def raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    except Exception as ex:                      # noqa: BLE001
        print('  unexpected', type(ex).__name__, ex)
        return False
    return False


def write_overlay(d, name, recs):
    with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
        for r in recs:
            fh.write((r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)) + '\n')


def synth_db():
    def hw(i, ja, en, slot, extra=''):
        return {'id': 'X/T.BIN#%x' % (0x100 + 8 * i), 'ja': ja, 'en': en, 'max_bytes': 40, 'slot': slot, 'refs': 1,
                'ctx': 'hwptr tbl@40[%d/8]%s stride-table(in-place only)' % (i, extra), 'fmt': 'hwptr'}
    recs = [hw(0, 'ｼｴﾛ', 'Sie', 4), hw(1, 'ﾛｯｻ', 'Ros', 4), hw(2, 'ﾁｪｺ', 'CZE', 4), hw(3, 'ﾌﾞﾗｼﾞﾙ', 'Brazil', 8)]
    pool = hw(4, 'ｱｲｳ', 'Ai', 4)
    pool['refs'] = 0
    pool['ctx'] = 'hwpool run=9 stride-table(in-place only)'
    recs.append(pool)
    recs.append({'id': 'X/T.BIN#900', 'ja': 'ﾜｼﾝﾄﾝ', 'en': 'Wash.', 'max_bytes': 14, 'refs': None,
                 'ctx': 'recarray S=30 n=9 W=14 modeshare=1.00 stride-table(in-place only)', 'fmt': 'recarr'})
    recs.append({'id': 'X/T.BIN#a00', 'ja': '八戸市', 'en': 'Hachin.', 'max_bytes': 8, 'refs': 1, 'ctx': 'tbl@2e98c[93/1270] interior-ptrs=1'})
    recs.append({'id': 'X/T.BIN#b00', 'ja': '横浜FC', 'en': 'Yoko.FC', 'max_bytes': 8, 'refs': 1, 'ctx': 'ptr@224a4'})
    recs.append({'id': 'X/T.BIN#c00', 'ja': 'ｱｶｼ', 'en': '', 'max_bytes': 40, 'slot': 4, 'refs': 1, 'ctx': 'hwptr ptr@8', 'fmt': 'hwptr'})
    return {'X/T.BIN': recs}


def ov(rid, ja, en, cls='other', why='test'):
    return {'id': rid, 'ja': ja, 'en': en, 'why': why, 'cls': cls}


# ------------------------------------------------------------------ 1. unit
def test_unit():
    td = tempfile.mkdtemp(prefix='refit_t_')
    try:
        # malformed
        for i, bad in enumerate(['not json', '[1]', '{"id":"X#1","en":"a"}', '{"id":"X#1","en":"a","why":"w","cls":"zzz"}',
                                 '{"id":"X1","en":"a","why":"w"}', '{"id":"X#1","en":"","why":"w"}']):
            d = os.path.join(td, 'bad%d' % i)
            os.makedirs(d)
            write_overlay(d, 'A.jsonl', [bad])
            check(raises(lambda d=d: R.read_all(d)), 'malformed overlay record %d refused' % i)
        d = os.path.join(td, 'dup')
        os.makedirs(d)
        write_overlay(d, 'A.jsonl', [ov('X/T.BIN#100', 'ｼｴﾛ', 'Cielo')])
        write_overlay(d, 'B.jsonl', [ov('X/T.BIN#100', 'ｼｴﾛ', 'Cielo')])
        check(raises(lambda: R.read_all(d)), 'duplicate id across overlay files refused')
        d0 = os.path.join(td, 'none')
        check(R.load_overlays(synth_db(), d0) == [], 'missing overlay directory = nothing to apply')
        check(R.overlay_files(d0) == [], 'missing directory lists no file')

        d = os.path.join(td, 'ok')
        os.makedirs(d)
        recs = [ov('X/T.BIN#100', 'ｼｴﾛ', 'Cielo', 'club'),                 # hwptr, needs 6 bytes, slot 4: relocation
                ov('X/T.BIN#108', 'ﾛｯｻ', 'Ros', 'club'),                   # same English: no change
                ov('X/T.BIN#110', 'ﾁｪｺ', 'Czech', 'nation'),
                ov('X/T.BIN#118', 'ﾌﾞﾗｼﾞﾙ', 'Brasil', 'nation'),             # fits the slot of 8 in place
                ov('X/T.BIN#120', 'ｱｲｳ', 'Aiueo', 'person'),                # hwpool: in place only, slot 4: does not fit
                ov('X/T.BIN#900', 'ﾜｼﾝﾄﾝ', 'Washington', 'person'),         # recarr 14: in place
                ov('X/T.BIN#a00', '八戸市', 'Hachinohe', 'town'),            # interior pointer: fixed 8: does not fit
                ov('X/T.BIN#b00', '横浜FC', 'Yokohama', 'jclub'),            # ptr text: movable (the pool decides)
                ov('X/T.BIN#c00', 'ｱｶｼ', 'Akashi', 'person'),               # untranslated
                ov('X/T.BIN#999', 'ｱ', 'A')]                                # unknown id
        stale = ov('X/T.BIN#900', 'ﾜｼﾝ', 'Washington')
        write_overlay(d, 'X__T.BIN.jsonl', recs)
        db = synth_db()
        rep = R.Report()
        mod = R.load_overlays(db, d, True, rep)
        ids = sorted(r['id'] for r in mod)
        check(ids == ['X/T.BIN#100', 'X/T.BIN#110', 'X/T.BIN#118', 'X/T.BIN#900', 'X/T.BIN#b00'], 'load_overlays returns the modified records: %s' % ids)
        d0 = {r['id']: r for r in synth_db()['X/T.BIN']}
        for r in db['X/T.BIN']:
            o = d0[r['id']]
            diff = {k for k in r if r[k] != o.get(k)}
            check(diff <= {'en'}, 'only en may change (%s: %s)' % (r['id'], diff))
        by = {r['id']: r for r in db['X/T.BIN']}
        check(by['X/T.BIN#100']['en'] == 'Cielo' and by['X/T.BIN#110']['en'] == 'Czech', 'hwptr refit applied (relocatable, budget 40)')
        check(by['X/T.BIN#108']['en'] == 'Ros', 'same English: untouched')
        check(by['X/T.BIN#120']['en'] == 'Ai', 'hwpool record (in place only): 6 bytes do not fit the slot of 4 -> skipped')
        check(by['X/T.BIN#a00']['en'] == 'Hachin.', 'interior-pointer record: 10 bytes do not fit the fixed 8 -> skipped')
        check(by['X/T.BIN#900']['en'] == 'Washington', 'record array: fits 14 in place')
        check(by['X/T.BIN#b00']['en'] == 'Yokohama', 'movable plain text: left to the pool repacking')
        check(by['X/T.BIN#c00']['en'] == '', 'untranslated record never translated by a refit')
        codes = {(i, c) for i, c, _m in rep.skipped}
        check(('X/T.BIN#999', 'unknown-id') in codes, 'unknown id skipped')
        check(('X/T.BIN#c00', 'untranslated') in codes, 'untranslated skipped')
        check(('X/T.BIN#120', 'cap') in codes and ('X/T.BIN#a00', 'cap') in codes, 'cap skips reported: %s' % sorted(codes))
        check(rep.before['X/T.BIN#100'] == 'Sie', 'report.before keeps the old English')

        # relocation off: only what fits the in-place slot
        db = synth_db()
        rep = R.Report()
        R.load_overlays(db, d, False, rep)
        by = {r['id']: r for r in db['X/T.BIN']}
        check(by['X/T.BIN#100']['en'] == 'Sie' and by['X/T.BIN#110']['en'] == 'CZE', 'relocate=False: forms above the slot skipped')
        check(by['X/T.BIN#118']['en'] == 'Brasil', 'relocate=False: a form that fits the slot is applied (%s)' % by['X/T.BIN#118']['en'])
        check(('X/T.BIN#100', 'needs-reloc') in {(i, c) for i, c, _m in rep.skipped}, 'needs-reloc reported')

        # stale ja
        d2 = os.path.join(td, 'stale')
        os.makedirs(d2)
        write_overlay(d2, 'S.jsonl', [stale])
        db = synth_db()
        rep = R.Report()
        check(R.load_overlays(db, d2, True, rep) == [] and rep.skipped and rep.skipped[0][1] == 'stale', 'stale ja skipped')

        # copy on write
        db = synth_db()
        snap = json.dumps(db, sort_keys=True)
        new, rep = R.apply_overlays(db, d, True)
        check(json.dumps(db, sort_keys=True) == snap, 'apply_overlays leaves the input DB untouched')
        nb = {r['id']: r for r in new['X/T.BIN']}
        check(nb['X/T.BIN#100']['en'] == 'Cielo' and len(new['X/T.BIN']) == len(db['X/T.BIN']), 'apply_overlays returns the refit DB')
        db1 = synth_db()
        db2 = synth_db()
        R.load_overlays(db1, d, True)
        R.load_overlays(db2, d, True)
        check(json.dumps(db1, sort_keys=True) == json.dumps(db2, sort_keys=True), 'deterministic')
        R.load_overlays(db1, d, True)
        check(json.dumps(db1, sort_keys=True) == json.dumps(db2, sort_keys=True), 'idempotent: a second load changes nothing')

        # validate: class caps, px, encoding
        d3 = os.path.join(td, 'val')
        os.makedirs(d3)
        write_overlay(d3, 'V.jsonl', [ov('X/T.BIN#100', 'ｼｴﾛ', 'Cielo', 'club'),
                                      ov('X/T.BIN#108', 'ﾛｯｻ', 'Rossarossa', 'club'),              # 10 chars > club cap 8
                                      ov('X/T.BIN#110', 'ﾁｪｺ', 'Czech Republic of Bohemia', 'nation'),   # too wide
                                      ov('X/T.BIN#118', 'ﾌﾞﾗｼﾞﾙ', 'Brásil', 'nation')])          # not cp932 ASCII-able? (a-acute is cp932)
        rep = R.validate(synth_db(), d3, True)
        pc = {(i, c) for i, c, _m in rep.problems}
        check(('X/T.BIN#108', 'chars') in pc, 'club cap of 8 characters enforced: %s' % sorted(pc))
        check(('X/T.BIN#110', 'px') in pc or ('X/T.BIN#110', 'chars') in pc, 'width cap enforced')
        check(('X/T.BIN#100', 'chars') not in pc and ('X/T.BIN#100', 'px') not in pc, 'a fitting form passes')
        rep = R.validate(synth_db(), d, True)
        check(rep.checked == len(R.read_all(d)[0][1]), 'validate counts every record')
        # table width: the widest Japanese string of the table is the pixel budget
        db = synth_db()
        rec = db['X/T.BIN'][2]
        check(R.family_cap_px(db, rec) >= 12 * len(R._enc('ﾌﾞﾗｼﾞﾙ')), 'family cap = widest Japanese string of the table')
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ------------------------------------------------------------------ 2. kana
def test_kana():
    cases = {'ｲｼﾊﾗ': 'Ishihara', 'ｱﾝﾄﾞｳ': 'Ando', 'ｵｵﾉ': 'Ono', 'ｲﾄｳ': 'Ito', 'ｶﾜﾉ': 'Kawano', 'ｶﾂﾔ': 'Katsuya',
             'ｼｬﾘ': 'Shari', 'ﾁｬﾉ': 'Chano', 'ﾂｶﾞﾙ': 'Tsugaru', 'ﾆｯﾎﾟﾝ': 'Nippon', 'ｲ ｲﾙﾁｪ': 'I Iruche', 'ﾊﾞﾝﾌﾞ': 'Banbu',
             'ｱﾗｲ': 'Arai', 'ﾕｳｷ': 'Yuki', 'ｼﾞｭﾝ': 'Jun', 'ﾌｼﾞﾓﾄ': 'Fujimoto'}
    for ja, en in cases.items():
        check(K.hepburn(ja) == en, 'hepburn(%s) = %s, got %s' % (ja, en, K.hepburn(ja)))
    check(K.hepburn('ABC') is None and K.hepburn('') is None and K.hepburn('漢字') is None, 'hepburn: non-kana -> None')


# ------------------------------------------------------------------ 3. real data
def digest(db):
    h = hashlib.sha256()
    for s in sorted(db):
        for r in db[s]:
            h.update(r['id'].encode())
            h.update((r.get('en') or '').encode())
    return h.hexdigest()


def test_real(quick):
    import build_patch as BP
    db = BP.load_tdb('translation')
    d0 = digest(db)
    files = R.read_all()
    check(files, 'translation/refit has overlay files (run tools/re/rfit_gen.py)')
    idx = R.index_db(db)
    n = 0
    cls = {}
    for path, recs in files:
        base = os.path.basename(path)
        for r in recs:
            n += 1
            cls[r.get('cls', 'other')] = cls.get(r.get('cls', 'other'), 0) + 1
            rec = idx.get(r['id'])
            check(rec is not None, '%s: id %s exists' % (base, r['id']))
            if rec is None:
                continue
            check(R.source_of(r['id']).replace('/', '__') + '.jsonl' == base, '%s: file named after the source of %s' % (base, r['id']))
            check(r.get('ja') == rec['ja'], '%s: ja of %s matches the DB' % (base, r['id']))
            check(bool(rec.get('en')) and r['en'] != rec['en'], '%s: %s refits a translated record and changes it' % (base, r['id']))
            check(all(32 <= ord(c) < 127 for c in r['en']), '%s: %s English is printable ASCII' % (base, r['id']))
    print('  real overlays: %d records in %d files %s' % (n, len(files), cls))
    import hwguard
    denied = hwguard.load_deny()
    rep = R.validate(db, relocate=True)
    # a refit form of a record that is on translation/hw_inplace.tsv (a table base: never moves) is refused by design (field cap = the slot)
    check(all(p[0] in denied and p[1] == 'cap' for p in rep.problems), 'static validation of every overlay record passes (denied records excepted): %s' % rep.problems[:5])
    new, rep = R.apply_overlays(db, relocate=True)
    check(digest(db) == d0, 'apply_overlays does not touch the loaded DB')
    check(len(rep.modified) + len(rep.skipped) == n and all(i in denied for i, _c, _m in rep.skipped),
          'every overlay record applies with relocation on, denied records are skipped (%d of %d, skipped %d)' % (len(rep.modified), n, len(rep.skipped)))
    new_off, rep_off = R.apply_overlays(db, relocate=False)
    for r in rep_off.modified:
        if r.get('fmt') == 'hwptr':
            check(len(R._enc(r['en'])) + 1 <= R.slot_of(r), 'relocate=False: %s fits its in-place slot' % r['id'])
    check(len(rep_off.modified) <= len(rep.modified), 'relocate=False applies a subset')
    # consistency: one club word / J.League name -> one English in every overlay; nations / cities may differ only by the
    # alternative form chosen for a narrower table (pixel cap), never to something that is not one of the alternatives
    seen = {}
    for path, recs in files:
        for r in recs:
            if r.get("cls") in ("club", "jclub", "nation", "city"):
                seen.setdefault((r["ja"], r["cls"]), set()).add(r["en"])
    check(all(len(v) == 1 for k, v in seen.items() if k[1] in ("club", "jclub")),
          "club words / J.League names are the same in every overlay: %s" % [(k, v) for k, v in seen.items() if k[1] in ("club", "jclub") and len(v) != 1][:3])
    check(all(len(v) <= 2 for v in seen.values()), "nation / city forms use at most two alternatives: %s" % [(k, v) for k, v in seen.items() if len(v) > 2][:3])
    forms = {}
    for line in open(os.path.join(ROOT, "translation", "refit", "forms.tsv"), encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            p = line.rstrip('\n').split('\t')
            forms[(p[1], p[0])] = [x.strip() for x in p[2].split(" | ")]
    for k, v in seen.items():
        if k in forms:
            check(v <= set(forms[k]), "overlay forms %s of %s are alternatives of forms.tsv %s" % (v, k, forms[k]))
    # the known rough forms of the task: placed in the overlays (club words, J.League names, nations, hometown composition)
    for ja, cls, en in (("ｼｴﾛ", "club", "Cielo"), ("ﾛｯｻ", "club", "Rosa"), ("ﾄｯﾎﾟﾘｰﾉ", "club", "Topolino"),
                        ("ｻﾝﾌﾚｯﾁｪ", "jclub", "Sanfrecce"), ("ｺﾝｻﾄﾞｰﾚ", "jclub", "Consadole"), ("ｱﾙｾﾞﾝﾁﾝ", "nation", "Argentina")):
        check(seen.get((ja, cls)) == {en}, "known form %s -> %s is in the overlays: %s" % (ja, en, seen.get((ja, cls))))
    names = {}
    for path, recs in files:
        for r in recs:
            if r.get("cls") == "person":
                names.setdefault(r["ja"], set()).add(r["en"])
    check(names.get("ﾙﾓｽﾀｷﾑ") == {"Rumostakim"} and names.get("ｼｴﾗ") == {"Sierra"}, "Rumostk / Sie name forms are in the overlays")
    ids = {r["id"] for path, recs in files for r in recs}
    check("FLOW_PRG/AUTOSAVE.BIN#6a18c" not in ids and "FLOW_PRG/EVENT.BIN#e0ffc" not in ids,
          "Hachin. / Okushi. (interior pointer, cannot move) are NOT in the overlays")
    # the DB in the tree is not modified by this module (no overlay -> same DB)
    check(R.load_overlays(db, os.path.join(tempfile.gettempdir(), 'no_such_refit_dir_xyz')) == [], 'no overlay -> nothing changes')
    check(digest(db) == d0, 'DB still untouched')
    return db


# ------------------------------------------------------------------ 4. real build code
def test_build(db, quick):
    files = R.read_all()
    touched = sorted({R.source_of(r['id']) for _p, recs in files for r in recs})
    if quick:
        pick = [s for s in ('FLOW_PRG/DRAFT.BIN', 'FLOW_PRG/AUTOSAVE.BIN', 'FLOW_PRG/EVENT.BIN', 'ATFIRST/TITLE.BIN', 'FLOW_PRG/SELNAT.BIN') if s in touched]
        touched = pick or touched[:5]
    for reloc in (True, False):
        new, rep = R.apply_overlays(db, relocate=reloc)
        base = R.simulate_db(db, touched, reloc)
        after = R.simulate_db(new, touched, reloc, rep)     # with the report: the build gives forms back when there is no 4-byte aligned room
        added = 0
        for s in touched:
            bf, bs = base[s]
            af, as_ = after[s]
            if af - bf or as_ - bs:
                added += 1
                check(False, 'build (%s): %s gains failures with the overlay: %s %s' % (
                    'hw on' if reloc else 'hw off', s, sorted(af - bf)[:3], sorted(as_ - bs)[:3]))
        print('  build code, hw relocation %s: %d sources, %d with new failures, %d records modified' % (
            'on' if reloc else 'off', len(touched), added, len(rep.modified)))
        changed = {r['id'] for r in rep.modified}
        for s in touched:
            af = after[s][0]
            check(not (af & changed), 'build (%s): %s: no refit record fails' % ('hw on' if reloc else 'hw off', s))


def main():
    quick = '--quick' in sys.argv
    test_unit()
    test_kana()
    db = test_real(quick)
    test_build(db, quick)
    print('test_refit: %s' % ('%d FAILURES' % len(fails) if fails else 'all passed'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
