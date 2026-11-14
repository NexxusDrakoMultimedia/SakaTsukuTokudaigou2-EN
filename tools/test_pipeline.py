"""Self-test of tools/build_patch.py.   Run:  python -I -X utf8 tools/test_pipeline.py [--keep]

 A  no-op: the real translation/ DB (all 'en' empty) and an empty DB give NO patches and a disc whose
    5 track files are byte-identical to the originals (sha1) and whose .cue equals the original .cue.
 B  demo translation (3 strings): overlay in place + overlay relocation (FLOW_PRG/CHALDANI.BIN) and a data
    file (DPETC/MESSAGE.INI).  The OUTPUT disc is re-read with tools/gdrom.py: exactly those 2 files changed,
    1213 others byte-identical, and the changes are exactly the intended ones.
 C  failure handling: a string that cannot fit is reported, not silently written.
 D  extras on a second disc: --append-safe (CHALDANI `_end`), BPINFO both copies, font glyph hook, ZSARC
    container member replacement; plus the unedited-font no-op and BSS-overlay refusal checks.
 F  proportional font (--proportional-font, tools/fontpatch.py): hooks of the 98 overlays, cave + table in the 1ST_READ tail,
    left-aligned half-width glyphs; same-size patches that differ only in the declared bytes, composes with the text stage,
    deterministic, refuses a non-zero reserve; tools/fontcheck.py --quick (decode + interpreter); the live Lua script is
    current; one OUTPUT disc is re-read (exactly 102 files changed).
 G  English money format (--money-format, tools/moneypatch.py): 102 overlays hooked + cave in the 1ST_READ tail, same-size patches
    that differ only in the declared bytes, deterministic, composes with the text stage and with the proportional font (two
    caves, no overlap), refuses a non-zero reserve or a damaged function; tools/moneycheck.py --quick (decode + interpreter).
 E  layer 1 (pool repacking, the default overlay path): identity over all 114 images, synthetic translations at a
    1.2 / 0.8 length mix (mean 1.0 = more than the per-string slot, less than the pool) on 3 overlays: pointers
    resolve, only intended bytes change, output disc differs in exactly those 3 files; --share dup, forced
    rewrite and the append-safe fallback.  (B-D run with --repack off: they test the legacy textdb path.)
Needs ~3.5 GB free in build/out (outputs are deleted unless --keep).  Writes only under build/.
"""
import glob
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_patch as BP     # noqa: E402
import discbuild as D        # noqa: E402
import gdrom                 # noqa: E402
import textdb                # noqa: E402
import textfmt_ini           # noqa: E402
import bzlib                 # noqa: E402
import font as F             # noqa: E402
import textrepack            # noqa: E402
import hashlib as _hl        # noqa: E402

T0 = time.time()
OUT = os.path.join(ROOT, 'build', 'out')
WORK = os.path.join(ROOT, 'build', 'test_pipeline')
ORIG_BASE = gdrom.BASE
KEEP = '--keep' in sys.argv
RESULTS = []

# The shipped translation/textures (repainted art) are real patches; these tests exercise the TEXT pipeline on their own DBs, so
# build_patches defaults to an empty textures directory here unless a test passes one (the texture stage has tools/test_texinject.py).
_NO_TEXTURES = os.path.join(WORK, 'no_textures')
_orig_build_patches = BP.build_patches


def _build_patches(*a, **kw):
    if len(a) < 14 and 'textures_dir' not in kw:
        os.makedirs(_NO_TEXTURES, exist_ok=True)
        kw['textures_dir'] = _NO_TEXTURES
    return _orig_build_patches(*a, **kw)


BP.build_patches = _build_patches


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    log(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        raise AssertionError(msg)


def orig_track(t):
    return os.path.join(ROOT, ORIG_BASE % t)


_orig_sha = {}


def orig_sha(t):
    if t not in _orig_sha:
        _orig_sha[t] = D.sha1_file(orig_track(t))
    return _orig_sha[t]


# ------------------------------------------------------------------ tdb helpers
def real_records(ids):
    """fetch real DB records by id from translation/*.jsonl"""
    want = set(ids)
    found = {}
    for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
        with open(p, encoding='utf8') as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r['id'] in want:
                    found[r['id']] = r
    missing = want - set(found)
    assert not missing, missing
    return found


def write_tdb(dirname, translations):
    """translations {id: en}; writes one jsonl per source from the real records"""
    shutil.rmtree(dirname, ignore_errors=True)
    os.makedirs(dirname)
    recs = real_records(translations)
    by = {}
    for rid, en in translations.items():
        r = dict(recs[rid])
        r['en'] = en
        by.setdefault(rid.rsplit('#', 1)[0].replace('/', '__'), []).append(r)
    for name, rs in by.items():
        with open(os.path.join(dirname, name + '.jsonl'), 'w', encoding='utf8', newline='\n') as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')


# ------------------------------------------------------------------ disc verification via gdrom
def read_output_disc(out_dir, name, expect_changed=None):
    """Re-read every file of the OUTPUT disc through tools/gdrom.py and compare with extracted/.
    Returns {changed path: new bytes}; asserts the file set is unchanged."""
    gdrom.BASE = ORIG_BASE
    orig_disc = gdrom.Disc(ROOT)
    orig_files = {p: (l, sz) for p, l, sz in gdrom.walk(orig_disc, *gdrom.pvd_root(orig_disc))}
    gdrom.BASE = name + ' (Track %d).bin'
    try:
        disc = gdrom.Disc(out_dir)
        files = list(gdrom.walk(disc, *gdrom.pvd_root(disc)))
        flist = {}
        with open(os.path.join(ROOT, 'extracted', '_filelist.tsv'), encoding='utf8') as f:
            for line in f:
                p = line.rstrip('\r\n').split('\t')
                if len(p) >= 3 and p[1].isdigit():
                    flist[p[0]] = int(p[2])
        check(len(files) == len(flist) == 1215, 'output disc has the same %d files as the original' % len(flist))
        check({p for p, _, _ in files} == set(flist), 'output disc file name set is identical')
        changed = {}
        same = 0
        for p, lba, size in files:
            olba, osize = orig_files[p]            # compare against the ORIGINAL disc (BCAST.BIN is not in extracted/)
            orig = orig_disc.read(olba, osize)
            new = disc.read(lba, size)
            if new == orig:
                same += 1
            else:
                changed[p] = new
        log('  re-read %d files: %d identical, %d changed: %s' % (len(files), same, len(changed), sorted(changed)))
        return changed, same
    finally:
        gdrom.BASE = ORIG_BASE


def cleanup_disc(out_dir, name):
    if KEEP:
        return
    for t in range(1, 6):
        p = D.track_path(out_dir, name, t)
        if os.path.exists(p):
            os.remove(p)
    for ext in ('.cue', '.gdi'):
        p = os.path.join(out_dir, name + ext)
        if os.path.exists(p):
            os.remove(p)


# ------------------------------------------------------------------ test A
def test_noop():
    log('--- A: no-op')
    # The real DB now carries English, so the no-op property is tested on a copy with every en blanked.
    blank = os.path.join(WORK, 'tdb_real_blank')
    shutil.rmtree(blank, ignore_errors=True)
    os.makedirs(blank)
    for name in os.listdir('translation'):
        if not name.endswith('.jsonl'):
            continue
        with open(os.path.join('translation', name), encoding='utf8', newline='') as fi, \
                open(os.path.join(blank, name), 'w', encoding='utf8', newline='') as fo:
            for line in fi:
                if line.strip():
                    r = json.loads(line)
                    r['en'] = ''
                    r.pop('skip', None)
                    line = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + ('\n' if line.endswith('\n') else '')
                fo.write(line)
    res = BP.build_patches(blank)
    t = res.totals()
    check(t['with_en'] == 0 and t['records'] > 100000, 'real translation DB (en blanked): %d records, %d with English' % (t['records'], t['with_en']))
    check(res.patches == {}, 'no patches from the empty translation')
    empty = os.path.join(WORK, 'tdb_empty')
    shutil.rmtree(empty, ignore_errors=True)
    os.makedirs(empty)
    check(BP.build_patches(empty).patches == {}, 'no patches from an empty DB directory')
    # en == '' must keep the original even for every record present; also whitespace-free check
    name = 'pipe-noop'
    res.disc = D.build_disc(res.patches, OUT, name, ROOT)
    for t_ in range(1, 6):
        a = D.sha1_file(D.track_path(OUT, name, t_))
        check(a == orig_sha(t_), 'no-op disc track %d byte-identical to original (sha1 %s..)' % (t_, a[:12]))
    check(res.disc['new_end_lba'] == res.disc['orig_end_lba'] and res.disc['moves'] == [], 'no-op: no file moved, disc not grown')
    with open(os.path.join(ROOT, 'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan).cue'), 'rb') as f:
        ocue = f.read()
    with open(os.path.join(OUT, name + '.cue'), 'rb') as f:
        ncue = f.read()
    # the generated cue references "<name> (Track N).bin"; compare after substituting the base name
    check(ncue.replace(name.encode(), b'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan)') == ocue,
          'no-op: generated .cue equals the original .cue (modulo base name)')
    cleanup_disc(OUT, name)


# ------------------------------------------------------------------ test B
ID_INPLACE = 'FLOW_PRG/CHALDANI.BIN#a80c'     # 70 bytes of room
ID_RELOC = 'FLOW_PRG/CHALDANI.BIN#bd9c'       # 8 bytes of room
ID_DATA = 'DPETC/MESSAGE.INI#22'
EN_INPLACE = 'Pick a rank.\nA: OK'
EN_RELOC = 'Yuta Minami (Goalkeeper)'
EN_DATA = 'Connecting to host...'


def test_demo():
    log('--- B: demo translation (3 strings)')
    tdb = os.path.join(WORK, 'tdb_demo')
    write_tdb(tdb, {ID_INPLACE: EN_INPLACE, ID_RELOC: EN_RELOC, ID_DATA: EN_DATA})
    res = BP.build_patches(tdb, repack=False)
    t = res.totals()
    check(t['with_en'] == 3 and t['applied'] == 3 and t['failed'] == 0 and t['skipped'] == 0,
          'demo: 3 strings applied (failed 0, skipped 0)')
    ov = [f for f in res.files if f.kind == 'overlay'][0]
    check(ov.relocated == 1 and ov.in_place == 1 and ov.appended == 0, 'demo overlay: 1 in place + 1 relocated, 0 appended (%s)' % ov.iso)
    check(set(res.patches) == {'/FLOW_PRG/CHALDANI.BIN', '/DPETC/MESSAGE.INI'}, 'demo: exactly 2 files patched: %s' % sorted(res.patches))
    check(len(res.patches['/FLOW_PRG/CHALDANI.BIN']) == ov.old_size, 'overlay size unchanged (%d)' % ov.old_size)
    res2 = BP.build_patches(tdb, repack=False)
    check(BP.patches_digest(res.patches) == BP.patches_digest(res2.patches), 'demo: two runs give identical patches (deterministic)')

    name = 'pipe-demo'
    res.disc = D.build_disc(res.patches, OUT, name, ROOT)
    BP.print_summary(res)
    changed, same = read_output_disc(OUT, name)
    check(set(changed) == {'/FLOW_PRG/CHALDANI.BIN', '/DPETC/MESSAGE.INI'} and same == 1213,
          'OUTPUT disc: exactly the 2 intended files changed, 1213 files byte-identical')
    for p, b in changed.items():
        check(b == res.patches[p], '%s on the output disc equals the patched bytes' % p)

    # --- overlay semantics
    src = 'FLOW_PRG/CHALDANI.BIN'
    old_img = textdb.load_image(src)
    new_img = textdb.Image(src, changed['/' + src], old_img.base)
    ostrs, optrs, _ = textdb.extract_image(old_img)
    by_old = {s.off: s for s in ostrs}
    nptrs = textdb.find_pointers(new_img)
    d = new_img.data
    for rid, en in ((ID_INPLACE, EN_INPLACE), (ID_RELOC, EN_RELOC)):
        s = by_old[int(rid.rsplit('#', 1)[1], 16)]
        targets = set()
        for w in s.refs:
            tgt = nptrs[w]
            e = d.index(b'\0', tgt)
            check(textdb.decode_text(d[tgt:e]) == en, '%s: pointer @%#x now resolves to the English text' % (rid, w))
            targets.add(tgt)
        check(len(s.refs) == 1, '%s: all %d pointer(s) rewritten' % (rid, len(s.refs)))
    check(nptrs[by_old[0xa80c].refs[0]] == 0xa80c, 'in-place string kept its offset')
    check(nptrs[by_old[0xbd9c].refs[0]] != 0xbd9c, 'relocated string moved')
    moved_ptr_words = {by_old[0xa80c].refs[0], by_old[0xbd9c].refs[0]}
    check(all(nptrs.get(w) == optrs.get(w) for w in optrs if w not in moved_ptr_words) and set(nptrs) == set(optrs),
          'all other pointer words unchanged')
    nstrs, _, _ = textdb.extract_image(new_img)
    nby = {s.off: s for s in nstrs}
    untouched = [s for s in ostrs if s.off not in (0xa80c, 0xbd9c)]
    check(all(nby.get(s.off) is not None and nby[s.off].raw == s.raw for s in untouched),
          'all %d other strings are byte-identical at the same offsets' % len(untouched))
    diff = [i for i in range(len(d)) if d[i] != old_img.data[i]]
    inside = set()
    for off in (0xa80c, 0xbd9c):
        inside.update(range(off, off + by_old[off].max_bytes))
    inside.update(by_old[0xa80c].refs[0] + k for k in range(4))
    inside.update(by_old[0xbd9c].refs[0] + k for k in range(4))
    # relocation destination = freed tail of the shortened string
    dest = nptrs[by_old[0xbd9c].refs[0]]
    inside.update(range(dest, dest + len(EN_RELOC) + 1))
    check(set(diff) <= inside, 'every changed byte (%d) lies in a translated string region or its pointer word' % len(diff))
    # --- data file semantics
    ini_old = BP.read_extracted('DPETC/MESSAGE.INI')
    ini_new = changed['/DPETC/MESSAGE.INI']
    eo, en_ = textfmt_ini.extract(ini_old), textfmt_ini.extract(ini_new)
    check(len(eo) == len(en_) and en_[0]['ja'] == EN_DATA and [e['ja'] for e in en_[1:]] == [e['ja'] for e in eo[1:]],
          'MESSAGE.INI: string 0 is English, the other %d strings unchanged' % (len(eo) - 1))
    lo, ln = ini_old.split(b'\r\n'), ini_new.split(b'\r\n')
    check(len(lo) == len(ln) and sum(1 for a, b in zip(lo, ln) if a != b) == 1, 'MESSAGE.INI: exactly one line differs')
    cleanup_disc(OUT, name)


# ------------------------------------------------------------------ test C
def test_failures():
    log('--- C: failure handling')
    tdb = os.path.join(WORK, 'tdb_fail')
    # find an orphan (cannot be relocated) in CHALDANI and give it an over-long text; plus a stale ja
    orph = real_records(['FLOW_PRG/EVENT.BIN#dbf2'])['FLOW_PRG/EVENT.BIN#dbf2']      # orphan: in place only, 5 bytes
    assert orph.get('orphan') and orph['max_bytes'] == 5
    shutil.rmtree(tdb, ignore_errors=True)
    os.makedirs(tdb)
    recs = [dict(orph, en='X' * 50)]
    recs.append({'id': 'FLOW_PRG/EVENT.BIN#aae80', 'ja': 'WRONG JA', 'en': 'stale', 'max_bytes': 24, 'refs': 1, 'ctx': ''})
    with open(os.path.join(tdb, 'FLOW_PRG__EVENT.BIN.jsonl'), 'w', encoding='utf8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    res = BP.build_patches(tdb)
    f = res.files[0]
    check(len(f.failed) == 1 and len(f.skipped) == 1, 'over-long orphan reported as failed (%d), stale ja skipped (%d)' % (len(f.failed), len(f.skipped)))
    check(res.patches == {}, 'nothing written when nothing could be applied')
    # unencodable English is rejected, not written
    write_tdb(tdb, {ID_DATA: 'café ☃'})
    res = BP.build_patches(tdb)
    check(res.patches == {} and len(res.files[0].skipped) == 1, 'unencodable English (snowman) skipped with a message')


# ------------------------------------------------------------------ test D
def modified_half_sheet(dirname):
    os.makedirs(dirname, exist_ok=True)
    f = F.Font.load()
    F.export_edit_sheet(f, os.path.join(dirname, 'edit_full.png'))
    F.export_edit_sheet(f, os.path.join(dirname, 'edit_half.png'), half=True)
    w, h, rows = F.read_png(os.path.join(dirname, 'edit_half.png'))
    rows = [bytearray(r) for r in rows]
    gi = F.half_index(ord('E'))
    x0, y0 = (gi % 32) * 12, (gi // 32) * 24
    for y in range(4, 10):               # draw a solid bar into glyph 'E'
        for x in range(2, 9):
            rows[y0 + y][x0 + x] = 0
    return w, h, rows, gi


def test_extras():
    log('--- D: extras')
    # D1 unedited font sheets are a no-op
    fd = os.path.join(WORK, 'font_unedited')
    shutil.rmtree(fd, ignore_errors=True)
    modified_half_sheet(fd)  # exports both sheets; the half sheet is overwritten below with the original
    f0 = F.Font.load()
    F.export_edit_sheet(f0, os.path.join(fd, 'edit_half.png'), half=True)
    empty = os.path.join(WORK, 'tdb_empty')
    r = BP.build_patches(empty, font_dir=fd)
    check(r.patches == {}, 'unedited font sheets -> no FONT.BIN change (ATFIRST glyph 3580 untouched)')
    # D2 BSS overlay refuses append-safe
    ids = [json.loads(l)['id'] for l in open(os.path.join(ROOT, 'translation', 'FLOW_PRG__MEETING.BIN.jsonl'), encoding='utf8')][:1]
    tdb = os.path.join(WORK, 'tdb_bss')
    write_tdb(tdb, {ids[0]: 'Z' * 400})
    r = BP.build_patches(tdb, repack=False, append_safe=True, members_dir=os.path.join(WORK, 'none'), font_dir=os.path.join(WORK, 'none'))
    f = r.files[0]
    check(len(f.failed) == 1 and r.patches == {} and any('not eligible' in n for n in f.notes),
          'append-safe refuses a BSS overlay (MEETING.BIN): string reported failed, file unchanged')
    # D3 full extras
    tdb = os.path.join(WORK, 'tdb_extras')
    long_en = 'Yuta Minami, goalkeeper of the national team, known for long saves. ' * 6
    write_tdb(tdb, {ID_RELOC: long_en, 'ETC_DATA/BPINFO.BIN#40': 'Kawamoto Oni', 'ETC_DATA/BPINFO.BIN#9c': 'Way Too Long Name Here'})
    r0 = BP.build_patches(tdb, repack=False, font_dir=os.path.join(WORK, 'none'), members_dir=os.path.join(WORK, 'none'))
    fo = [x for x in r0.files if x.kind == 'overlay'][0]
    check(len(fo.failed) == 1 and '/FLOW_PRG/CHALDANI.BIN' not in r0.patches,
          'without --append-safe the long overlay string FAILS and the overlay is untouched')
    bp = [x for x in r0.files if x.kind == 'bpinfo']
    check(len(bp) == 2 and bp[0].applied == 1 and len(bp[0].failed) == 1 and all(x.changed for x in bp), 'BPINFO: 12-char name applied, 22-char name rejected (counted once, both copies patched)')
    # member + font
    members = os.path.join(WORK, 'members')
    shutil.rmtree(members, ignore_errors=True)
    cont = 'GAME/ACCESSRY.ZAR'
    cdata = BP.read_extracted(cont)
    cm = bzlib.parse_archive(cdata)[0]
    mname = cm[3].name
    mplain = cm[3].extract()
    newplain = mplain + b'PATCHED-MEMBER-DATA' * 7
    os.makedirs(os.path.join(members, *cont.split('/')))
    with open(os.path.join(members, *cont.split('/'), mname), 'wb') as f:
        f.write(newplain)
    fd2 = os.path.join(WORK, 'font_edit')
    shutil.rmtree(fd2, ignore_errors=True)
    w, h, rows, gi = modified_half_sheet(fd2)
    F.write_png(os.path.join(fd2, 'edit_half.png'), w, h, rows)
    res = BP.build_patches(tdb, repack=False, append_safe=True, font_dir=fd2, members_dir=members)
    want = {'/FLOW_PRG/CHALDANI.BIN', '/ETC_DATA/BPINFO.BIN', '/ATFIRST/BPINFO.BIN', '/FONT.BIN', '/ATFIRST/FONT.BIN', '/' + cont}
    check(set(res.patches) == want, 'extras: patched file set == %s' % sorted(want))
    t = res.totals()
    ov = [x for x in res.files if x.kind == 'overlay'][0]
    check(ov.appended == 1 and not ov.failed, 'append-safe: overflow string appended after the no-BSS overlay')
    old = BP.read_extracted('FLOW_PRG/CHALDANI.BIN')
    new = res.patches['/FLOW_PRG/CHALDANI.BIN']
    grow = len(new) - len(old)
    check(grow >= len(long_en) and grow % 4 == 0, 'CHALDANI grew by %d bytes (4-aligned)' % grow)
    end_off = int(BP.load_survey()['CHALDANI.BIN']['end_var_off'], 16)
    check(struct.unpack_from('<I', new, end_off)[0] == 0x8c4d0000 + len(new) and struct.unpack_from('<I', old, end_off)[0] == 0x8c4d0000 + len(old),
          '`_end` word @%#x raised from %#x to %#x (= base + new size)' % (end_off, 0x8c4d0000 + len(old), 0x8c4d0000 + len(new)))
    BP.print_summary(res)

    name = 'pipe-extras'
    res.disc = D.build_disc(res.patches, OUT, name, ROOT)
    changed, same = read_output_disc(OUT, name)
    check(set(changed) == want and same == 1215 - len(want), 'OUTPUT disc: exactly the %d intended files changed, %d identical' % (len(want), same))
    for p in want:
        check(changed[p] == res.patches[p], '%s on the output disc equals the patched bytes' % p)
    # BPINFO
    import textfmt_bpinfo as BI
    for cp in ('ETC_DATA/BPINFO.BIN', 'ATFIRST/BPINFO.BIN'):
        e0 = BI.extract(BP.read_extracted(cp), cp)
        e1 = BI.extract(changed['/' + cp], cp)
        diff = [i for i, (a, b) in enumerate(zip(e0, e1)) if a['ja'] != b['ja']]
        check(diff == [0] and e1[0]['ja'] == 'Kawamoto Oni', '%s: only player 0 renamed (record 1 kept its Japanese name)' % cp)
        a, b = BP.read_extracted(cp), changed['/' + cp]
        bad = [i for i in range(len(a)) if a[i] != b[i] and not (0x40 <= i < 0x40 + 14)]
        check(not bad, '%s: all changed bytes are inside the first name field' % cp)
    # font
    for cp in BP.FONT_COPIES:
        fo_ = F.Font(BP.read_extracted(cp))
        fn_ = F.Font(changed['/' + cp])
        check(fo_.glyphs == fn_.glyphs, '%s: full-width glyphs unchanged' % cp)
        hd = [i for i in range(F.NHALF) if fo_.half()[i] != fn_.half()[i]]
        check(hd == [gi], '%s: exactly half-width glyph %d (E) differs' % (cp, gi))
        check(len(changed['/' + cp]) <= BP.FONT_LIMIT, '%s: %d bytes <= load slot %d' % (cp, len(changed['/' + cp]), BP.FONT_LIMIT))
    # container
    mem, tail = bzlib.parse_archive(changed['/' + cont])
    check(tail == len(changed['/' + cont]) and [m.name for m in mem] == [m.name for m in cm], 'container re-parses with all %d members in order' % len(mem))
    for a, b in zip(cm, mem):
        if a.name == mname:
            check(b.extract() == newplain and b.hdr_crc_ok and b.crc16 == bzlib.crc16(newplain), 'member %s replaced (crc16 + header CRC valid)' % mname)
        elif a.header != b.header or a.packed != b.packed:
            check(False, 'untouched member %s changed' % a.name)
    check(True, 'all %d other members byte-identical (header + packed data)' % (len(cm) - 1))
    check(all(m.offset % 4 == 0 for m in mem), 'all member records 4-byte aligned')
    cleanup_disc(OUT, name)


# ------------------------------------------------------------------ test F
def test_prop_font():
    log('--- F: proportional font (--proportional-font)')
    import fontpatch as FPT
    import fontcheck
    import font as F
    empty = os.path.join(WORK, 'tdb_empty')
    shutil.rmtree(empty, ignore_errors=True)
    os.makedirs(empty)
    check(BP.build_patches(empty).patches == {}, 'F: flag off (default) gives no patches')
    res = BP.build_patches(empty, prop_font=True)
    ov = sorted(p for p in res.patches if p.startswith('/FLOW_PRG/') or p == '/ATFIRST/HELP.BIN')
    check(len(res.patches) == 101 and len(ov) == 98 and {'/1ST_READ.BIN', '/FONT.BIN', '/ATFIRST/FONT.BIN'} <= set(res.patches),
          'F: 101 files patched = 98 overlays + 1ST_READ.BIN + both FONT.BIN copies (%d)' % len(res.patches))
    check(all(len(res.patches[p]) == len(BP.read_extracted(p[1:])) for p in res.patches), 'F: every patched file keeps its size')
    check(BP.patches_digest(res.patches) == BP.patches_digest(BP.build_patches(empty, prop_font=True).patches), 'F: deterministic')
    # overlays: only the declared hook regions differ, and they carry the cave entry addresses
    ct = FPT.placement()
    nbytes = 0
    for iso in ov:
        old, new = BP.read_extracted(iso[1:]), res.patches[iso]
        s = FPT.find_sites(old, iso)[0]
        n2 = len(FPT.H2_OLD[s['variant']])
        diff = [i for i in range(len(old)) if old[i] != new[i]]
        nbytes += len(diff)
        if not all(s['h1'] <= i < s['h1'] + 16 or s['h2'] <= i < s['h2'] + n2 for i in diff):
            check(False, 'F: %s changes bytes outside the hook regions' % iso)
        if new[s['h1']:s['h1'] + 16] != FPT.hook_h1(s['variant'], ct):
            check(False, 'F: %s H1 bytes' % iso)
    check(True, 'F: all 98 overlays differ only inside the two hook regions (%d bytes in total)' % nbytes)
    # 1ST_READ: cave + table, nothing else
    k0, k1 = BP.read_extracted('1ST_READ.BIN'), res.patches['/1ST_READ.BIN']
    diff = [i for i in range(len(k0)) if k0[i] != k1[i]]
    lo, hi = ct[0] - FPT.IMG_BASE, ct[1] - FPT.IMG_BASE
    check(all(lo <= i < lo + FPT.CAVE_SIZE or hi <= i < hi + 256 for i in diff), 'F: 1ST_READ.BIN differs only in the cave and the table')
    check(k1[lo:lo + FPT.CAVE_SIZE] == FPT.cave_bytes(ct), 'F: cave bytes in 1ST_READ.BIN')
    tbl = k1[hi:hi + 256]
    check(tbl[0] == 12 and tbl[0x20] == 12 and all(tbl[b] == 12 for b in range(0x30, 0x3A)) and tbl[0x69] == 5 and tbl[0x57] == 13
          and not any(tbl[b] for b in range(0x80, 0xA0)), 'F: table: space 12, digits 12, i 5, W 13, no entries for 0x80-0x9f')
    # fonts: full-width glyphs untouched, half-width ASCII left aligned, digits and katakana untouched
    for copy in ('/FONT.BIN', '/ATFIRST/FONT.BIN'):
        base = F.Font(BP.read_extracted(copy[1:]))
        f1 = F.Font(res.patches[copy])
        check(f1.glyphs == base.glyphs and f1.packed == base.packed and f1.hdr == base.hdr, 'F: %s full-width glyphs and header unchanged' % copy)
        h0, h1 = base.half(), f1.half()
        shifted = [b for b in range(256) if F.half_index(b) is not None and h0[F.half_index(b)] != h1[F.half_index(b)]]
        ok = all(0x21 <= b < 0x7F and b not in FPT.DIGITS for b in shifted)
        ok = ok and all(FPT.glyph_metrics(h1[F.half_index(b)])[0] == 0 for b in range(0x21, 0x7F) if b not in FPT.DIGITS)
        ok = ok and all(h1[F.half_index(b)] == FPT.shift_glyph_left(h0[F.half_index(b)], FPT.glyph_metrics(h0[F.half_index(b)])[0])
                        for b in shifted)
        check(ok and len(shifted) > 30, 'F: %s: %d half-width glyphs left-aligned (lossless shift), nothing else changed' % (copy, len(shifted)))
    h1 = F.Font(res.patches['/FONT.BIN']).half()
    check(all(tbl[b] >= FPT.glyph_metrics(h1[F.half_index(b)])[1] + 2 for b in range(0x21, 0x7F) if b not in FPT.DIGITS),
          'F: every advance leaves at least 1 blank pixel after the strong ink')
    # composition with the text stage (CHALDANI = variant A overlay, MESSAGE.INI) and the 'ABC' option
    tdb = os.path.join(WORK, 'tdb_demo_f')
    write_tdb(tdb, {ID_INPLACE: EN_INPLACE, ID_RELOC: EN_RELOC, ID_DATA: EN_DATA})
    base_res = BP.build_patches(tdb, repack=False)
    res2 = BP.build_patches(tdb, repack=False, prop_font=True)
    c0 = base_res.patches['/FLOW_PRG/CHALDANI.BIN']
    check(res2.patches['/FLOW_PRG/CHALDANI.BIN'] == FPT.patch_overlay(c0, 'CHALDANI')[0],
          'F: hooks compose on the text-patched overlay (signature scan on the current bytes)')
    check(res2.patches['/DPETC/MESSAGE.INI'] == base_res.patches['/DPETC/MESSAGE.INI'], 'F: unrelated text patches untouched')
    allv = BP.build_patches(empty, prop_font=True, prop_variants='ABC')
    check(len(allv.patches) == 101 + 7, 'F: variants ABC hook 7 more overlays (6 B + 1 C)')
    ctl = BP.build_patches(empty, prop_font=True, prop_glyphs=False)
    ck = ctl.patches['/1ST_READ.BIN'][hi:hi + 256]
    check(len(ctl.patches) == 99 and '/FONT.BIN' not in ctl.patches and ck == bytes([12]) * 256,
          'F: control mode: 98 overlays + 1ST_READ.BIN, fonts untouched, all-12 table (behaviour identical to the original)')
    # guards
    try:
        FPT.patch_1st_read(k1, tbl)
        check(False, 'F: patching an already patched 1ST_READ.BIN must be refused')
    except FPT.FontPatchError:
        check(True, 'F: patch_1st_read refuses a non-zero reserve')
    bad = bytearray(BP.read_extracted('FLOW_PRG/MEETING.BIN'))
    s = FPT.find_sites(bytes(bad))[0]
    bad[s['h2'] + 10] ^= 1
    try:
        FPT.find_sites(bytes(bad))
        check(False, 'F: a damaged wrap block must be refused')
    except FPT.FontPatchError:
        check(True, 'F: a damaged wrap block is refused (no silent half patch)')
    # static check + interpreter run, live script freshness
    check(fontcheck.main(['fontcheck', '--quick']) == 0,
          'F: tools/fontcheck.py --quick (capstone decode of every patched word, cave and layout function executed)')
    with open(os.path.join(HERE, 'emu', 'fonttest.lua'), encoding='utf8', newline='') as fh:
        check(fh.read() == FPT.lua_source(), 'F: tools/emu/fonttest.lua is current (regenerate with tools/fontpatch.py lua)')
    # OUTPUT disc
    name = 'pipe-propfont'
    res2.disc = D.build_disc(res2.patches, OUT, name, ROOT)
    changed, same = read_output_disc(OUT, name)
    check(set(changed) == set(res2.patches) and len(changed) == 102,
          'F: OUTPUT disc: exactly the %d intended files changed' % len(res2.patches))
    check(all(b == res2.patches[p_] for p_, b in changed.items()), 'F: every changed file on the output disc equals the patched bytes')
    cleanup_disc(OUT, name)


# ------------------------------------------------------------------ test G
def test_money():
    log('--- G: English money format (--money-format)')
    import moneypatch as MPT
    import patchengine as PE_
    import moneycheck
    import fontpatch as FPT
    empty = os.path.join(WORK, 'tdb_empty')
    shutil.rmtree(empty, ignore_errors=True)
    os.makedirs(empty)
    check(BP.build_patches(empty).patches == {}, 'G: flag off (the build_patches default) gives no patches')
    res = BP.build_patches(empty, money_fmt=True)
    check(len(res.patches) == 103 and '/1ST_READ.BIN' in res.patches, 'G: 102 overlays + 1ST_READ.BIN patched (%d files)' % len(res.patches))
    check(all(len(res.patches[p_]) == len(BP.read_extracted(p_[1:])) for p_ in res.patches), 'G: every patched file keeps its size')
    check(BP.patches_digest(res.patches) == BP.patches_digest(BP.build_patches(empty, money_fmt=True).patches), 'G: deterministic')
    hk = MPT.hook_bytes()
    dec = MPT.cave_symbols()['m_dec']
    nd = 0
    for iso in sorted(res.patches):
        if iso == '/1ST_READ.BIN':
            continue
        old, new = BP.read_extracted(iso[1:]), res.patches[iso]
        sites = MPT.find_sites(old, iso)
        diff = {i for i in range(len(old)) if old[i] != new[i]}
        want = set()
        for st in sites:
            if st['variant'] != 'A':
                continue
            want |= set(range(st['off'], st['off'] + 12))
            r = MPT.find_d_literal(old, st['off'])
            if r:
                want |= set(range(r[0], r[0] + 4))
                check(new[r[0]:r[0] + 4] == struct.pack('<I', dec), 'G: %s %%D literal' % iso)
                nd += 1
            check(new[st['off']:st['off'] + 12] == hk, 'G: %s hook bytes' % iso)
            if r:                                   # the compact-flag halfword of the scout info panel call sites (SCDRF / SEARCH, number-formats 4.7)
                for po in MPT.panel_sites(old, r[1] + st['off']):
                    want |= set(range(po, po + 2))
        # mn6 number-library / numeric wrappers (stub in the dead body of the money function + literal-pool words; GAME's text function hook):
        # the declared edits of those owners are allowed too (the test still refuses any other changed byte)
        es_ = PE_.EditSet()
        MPT.overlay_edits(es_, old, iso[1:])
        for e_ in es_.edits:
            if e_.owner.startswith('money.lib'):
                want |= set(range(e_.start, e_.end))
        if iso == '/' + MPT.TV_CARD['rel']:          # TV station card capital routine (moneypatch.patch_tv_card)
            t = MPT.TV_CARD
            want |= set(range(t['fn'], t['fn_end'])) | set(range(t['tail'], t['tail_end']))
            code, tail, _ = MPT.tv_card_bytes(t['base'] + sites[0]['off'])
            check(new[t['fn']:t['fn_end']] == code and new[t['tail']:t['tail_end']] == tail, 'G: TV_EVENT card routine bytes')
        if not diff <= want or not diff:
            check(False, 'G: %s differs outside the hook bytes / %%D literal' % iso)
    check(nd == 98, 'G: %%D literal redirected in 98 overlays (%d); LOGO OFFICE TITLE x2 have no expander' % nd)
    k0, k1 = BP.read_extracted('1ST_READ.BIN'), res.patches['/1ST_READ.BIN']
    lo = MPT.CAVE_ADDR - MPT.IMG_BASE
    cv = MPT.cave_bytes()
    # since mn6 the 1ST_READ tail also holds the number-library wrapper (money.lib) and the numeric wrapper (money.libn): three declared spans
    lib_b, libn_b = MPT.lib_bytes(), MPT.libn_bytes()
    lo_l, lo_n = MPT.LIB_ADDR - MPT.IMG_BASE, MPT.LIBN_ADDR - MPT.IMG_BASE
    spans = [(lo, lo + len(cv)), (lo_l, lo_l + len(lib_b)), (lo_n, lo_n + len(libn_b))]
    kdiff = [i for i in range(len(k0)) if k0[i] != k1[i]]
    check(all(any(a <= i < b for a, b in spans) for i in kdiff) and k1[lo:lo + len(cv)] == cv and k1[lo_l:lo_l + len(lib_b)] == lib_b
          and k1[lo_n:lo_n + len(libn_b)] == libn_b,
          'G: 1ST_READ.BIN differs only in the cave (%d bytes at %#x) and the two library wrappers (%d bytes at %#x, %d at %#x)' % (
              len(cv), MPT.CAVE_ADDR, len(lib_b), MPT.LIB_ADDR, len(libn_b), MPT.LIBN_ADDR))
    # money-only: no %D change
    mo = BP.build_patches(empty, money_fmt=True, money_decimal_d=False)
    check(len(mo.patches) == 103 and mo.patches['/FLOW_PRG/MEETING.BIN'] != res.patches['/FLOW_PRG/MEETING.BIN'],
          'G: money-only variant leaves the %D literal alone')
    # composition: text stage, proportional font (disjoint caves, both found by signature)
    tdb = os.path.join(WORK, 'tdb_demo_g')
    write_tdb(tdb, {ID_INPLACE: EN_INPLACE, ID_RELOC: EN_RELOC, ID_DATA: EN_DATA})
    base_res = BP.build_patches(tdb, repack=False)
    r2 = BP.build_patches(tdb, repack=False, money_fmt=True)
    c0 = base_res.patches['/FLOW_PRG/CHALDANI.BIN']
    check(r2.patches['/FLOW_PRG/CHALDANI.BIN'] == MPT.patch_overlay(c0, 'CHALDANI')[0], 'G: hooks compose on the text-patched overlay')
    check(r2.patches['/DPETC/MESSAGE.INI'] == base_res.patches['/DPETC/MESSAGE.INI'], 'G: unrelated text patches untouched')
    both = BP.build_patches(empty, money_fmt=True, prop_font=True)
    kb = both.patches['/1ST_READ.BIN']
    ct = FPT.placement()
    check(kb[lo:lo + len(cv)] == cv and kb[ct[0] - FPT.IMG_BASE:ct[0] - FPT.IMG_BASE + FPT.CAVE_SIZE] == FPT.cave_bytes(ct),
          'G: with the proportional font both caves are present')
    check(MPT.CAVE_ADDR >= ct[0] + FPT.RESERVE and MPT.CAVE_ADDR >= ct[1] + FPT.TABLE_SIZE, 'G: the two caves do not overlap')
    check(set(res.patches) <= set(both.patches), 'G: both patches cover the same overlays (%d files)' % len(both.patches))
    # guards
    try:
        MPT.patch_1st_read(k1)
        check(False, 'G: patching an already patched 1ST_READ.BIN must be refused')
    except MPT.MoneyPatchError:
        check(True, 'G: patch_1st_read refuses a non-zero reserve')
    bad = bytearray(BP.read_extracted('FLOW_PRG/MEETING.BIN'))
    off = MPT.find_sites(bytes(bad))[0]['off']
    bad[off + 0x60] ^= 1
    try:
        MPT.find_sites(bytes(bad))
        check(False, 'G: a damaged money function must be refused')
    except MPT.MoneyPatchError:
        check(True, 'G: a damaged money function is refused (no blind patch)')
    check(moneycheck.main(['moneycheck', '--quick']) == 0,
          'G: tools/moneycheck.py --quick (capstone decode, original + patched functions and the expander executed)')


# ------------------------------------------------------------------ test E
E_SOURCES = ('FLOW_PRG/CLUBEDIT.BIN', 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/SPF_READ.BIN')


def synth_en(raw, n):
    """deterministic ASCII English of n bytes (hex digits derived from the Japanese bytes: equal ja -> equal en)."""
    base = _hl.blake2b(raw, digest_size=64).hexdigest().encode()
    return (base * (n // len(base) + 1))[:n].decode()


def synth_translations(source):
    """{id: en} for EVERY string of an overlay: movable strings of multi-string pools alternate x1.2 / x0.8 (pool
    mean 1.0: single slots overflow, the pool does not), single-string pools and fixed strings x0.8."""
    img = textdb.load_image(source)
    strs, _, _ = textdb.extract_image(img)
    pools, where = textrepack.find_pools(strs)
    pool_of = {}
    for p in pools:
        for k, s in enumerate(p.home):
            pool_of[s.off] = (len(p.home), k)
    out = {}
    for s in strs:
        mp = pool_of.get(s.off)
        r = (1.2 if mp[1] % 2 == 0 else 0.8) if (mp and mp[0] > 1) else 0.8
        n = max(1, int(r * (len(s.raw) + 1)) - 1)
        out['%s#%x' % (source, s.off)] = synth_en(s.raw, n)
    return out, strs


def verify_overlay(src, old, new, strs, want, label):
    """independent semantic check of a patched overlay (does not use textrepack.check): every pointer word of
    every string resolves to the wanted text, orphans are written in place, and every changed byte is a pointer
    word of a movable string or lies inside the region of a movable / translated string."""
    base = textdb.load_image(src).base
    allowed = bytearray(len(old))
    nref = 0
    for s in strs:
        if textrepack.is_movable(s) or s.off in want:
            for k in range(s.off, s.off + s.max_bytes):
                allowed[k] = 1
        if textrepack.is_movable(s):
            for w in s.refs:
                for k in range(w, w + 4):
                    allowed[k] = 1
    diff = [i for i in range(len(old)) if old[i] != new[i]]
    check(len(new) == len(old), '%s %s: image size unchanged (%d)' % (label, src, len(new)))
    check(all(allowed[i] for i in diff), '%s %s: all %d changed bytes lie in a pool/string region or a pointer word' % (label, src, len(diff)))
    bad = 0
    nul = bytes(1)
    for s in strs:
        exp = want.get(s.off)
        exp = s.raw if exp is None else exp
        for w in s.refs:
            t = struct.unpack_from('<I', new, w)[0] - base
            if not 0 <= t < len(new) or new[t:new.index(nul, t)] != exp:
                bad += 1
        nref += len(s.refs)
        if not s.refs and s.off in want:      # orphans are written in place
            if new[s.off:s.off + len(exp)] != exp or new[s.off + len(exp)] != 0:
                bad += 1
    check(bad == 0, '%s %s: all %d pointer words resolve to the intended text (English or untouched Japanese), orphans in place' % (label, src, nref))
    return len(diff)


def test_repack():
    log('--- E: layer 1 pool repacking (default path)')
    # E1 identity over all images, both sharing modes
    n_id = 0
    for source, path in textdb.list_sources():
        if source == '1ST_READ.BIN':
            continue
        try:
            img = textdb.load_image(source, path)
        except ValueError:
            continue
        ex = textdb.extract_image(img)
        if not ex[0]:
            continue
        for share in ('none', 'dup'):
            new, rp = textrepack.repack(img.data, img.base, [], source=source, share=share, extracted=ex)
            if new != img.data:
                check(False, 'identity: %s share=%s differs from the original' % (source, share))
        n_id += 1
    check(n_id == 114, 'identity: repack with no translation returns the original bytes for all %d images (share none and dup)' % n_id)

    # E2 synthetic translation on 3 overlays
    tdb = os.path.join(WORK, 'tdb_repack')
    trans, strs_of, want_of = {}, {}, {}
    for src in E_SOURCES:
        t, strs = synth_translations(src)
        trans.update(t)
        strs_of[src] = strs
        want_of[src] = {int(k.rsplit('#', 1)[1], 16): v.encode('ascii') for k, v in t.items()}
    write_tdb(tdb, trans)
    legacy = BP.build_patches(tdb, repack=False)
    res = BP.build_patches(tdb)
    t = res.totals()
    ovs = [f for f in res.files if f.kind == 'overlay']
    nleg = sum(len(f.failed) for f in legacy.files if f.kind == 'overlay')
    log('  %d synthetic translations: legacy per-string path failed %d, repack failed %d' % (
        len(trans), nleg, sum(len(f.failed) for f in ovs)))
    check(t['with_en'] == len(trans) and t['skipped'] == 0, 'repack: %d synthetic strings loaded, none skipped' % len(trans))
    check(sum(len(f.failed) for f in ovs) <= nleg, 'repack fails no more strings than the legacy per-string path (%d <= %d)' % (sum(len(f.failed) for f in ovs), nleg))
    check(t['failed'] == 0 and t['applied'] == len(trans), 'repack: all %d strings applied, failed 0' % len(trans))
    check(set(res.patches) == {'/' + s for s in E_SOURCES}, 'repack: exactly the 3 overlays are patched: %s' % sorted(res.patches))
    check(BP.patches_digest(res.patches) == BP.patches_digest(BP.build_patches(tdb).patches), 'repack: two runs give identical bytes (deterministic)')
    for src in E_SOURCES:
        old = textdb.load_image(src).data
        verify_overlay(src, old, res.patches['/' + src], strs_of[src], want_of[src], 'repack')
    # E3 disc: only those 3 files differ
    name = 'pipe-repack'
    res.disc = D.build_disc(res.patches, OUT, name, ROOT)
    changed, same = read_output_disc(OUT, name)
    check(set(changed) == set(res.patches) and same == 1215 - 3, 'OUTPUT disc: exactly the 3 overlays changed, %d files byte-identical' % same)
    for p, b in changed.items():
        check(b == res.patches[p], '%s on the output disc equals the patched bytes' % p)
    cleanup_disc(OUT, name)
    # E4 --share dup: not worse
    r2 = BP.build_patches(tdb, share='dup')
    check(sum(len(f.failed) for f in r2.files if f.kind == 'overlay') <= t['failed'], 'share=dup places at least as many strings as share=none')
    for src in E_SOURCES:
        old = textdb.load_image(src).data
        verify_overlay(src, old, r2.patches['/' + src], strs_of[src], want_of[src], 'share=dup')
    # E5 forced rewrite of every pool of the 3 overlays is an equivalent image
    for src in E_SOURCES:
        img = textdb.load_image(src)
        ex = textdb.extract_image(img)
        new, rp = textrepack.repack(img.data, img.base, [], source=src, force=True, extracted=ex)
        bad = textrepack.check(img.data, new, img.base, ex[0], {}, rp)
        d = verify_overlay(src, img.data, new, ex[0], {}, 'forced')
        check(not bad and rp.repacked_pools == len(rp.pools),
              'forced rewrite of all %d pools of %s: text behind every pointer identical (%d bytes differ)' % (len(rp.pools), src, d))
    # E6 over-long string: repack reports it; the opt-in append-safe fallback still works for a no-BSS overlay
    tdb2 = os.path.join(WORK, 'tdb_repack_long')
    long_en = 'Yuta Minami, goalkeeper of the national team, known for long saves. ' * 6
    write_tdb(tdb2, {ID_RELOC: long_en})
    r0 = BP.build_patches(tdb2)
    f0 = r0.files[0]
    check(len(f0.failed) == 1 and r0.patches == {}, 'repack: over-long string reported as failed (pool full), overlay untouched')
    r1 = BP.build_patches(tdb2, append_safe=True)
    f1 = r1.files[0]
    check(not f1.failed and f1.appended == 1 and len(r1.patches['/FLOW_PRG/CHALDANI.BIN']) > f1.old_size,
          'opt-in --append-safe fallback after repack: appended 1 string, overlay grew by %d' % (f1.new_size - f1.old_size))


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    try:
        test_noop()
        test_demo()
        test_failures()
        test_extras()
        test_prop_font()
        test_money()
        test_repack()
    finally:
        gdrom.BASE = ORIG_BASE
    ok = sum(1 for c, _ in RESULTS if c)
    log('RESULT: %d checks passed, %d failed' % (ok, len(RESULTS) - ok))
    return 0 if ok == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
