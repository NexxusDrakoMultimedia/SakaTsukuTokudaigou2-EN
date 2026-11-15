"""build_patch: end-to-end English patch pipeline (translation DB -> patched files -> patched GD-ROM).

    python -I -X utf8 tools/build_patch.py [--tdb translation] [--out build/out] [--name SakaTsuku2-EN]
                                           [--repack on|off] [--share none|dup] [--no-cross-pool]
                                           [--append-safe] [--relocate-ptrblob] [--strict]
                                           [--dry-run] [--dump DIR] [--strategy gap|append]
                                           [--proportional-font on|off] [--money-format on|money-only|off]
                                           [--hw-relocate on|off|force] [--texture-policy exact|grow]
                                           [--prop-scale on|off] [--money-style jp|western] [--refit on|off]
                                           [--align-fix on|off] [--tag-fix on|off] [--scout-fix on|off]
                                           [--crowd-fix on|off] [--bcast-speed off|1.7|1.9|2.2] [--lin-center on|off] [--small-prop on|off]
                                           [--options-fix on|off] [--cell-prop on|off] [--clip-lead-space on|off]
                                           [--grow-overlays N] [--dedupe-files on|off] [--allow-overflow]
                                           [--add-file /ISO/PATH=LOCAL ...] [--verify-disc off|fast|full]
                                           [--club-guard on|off] [--club-dot on|off]
See docs/pipeline.md, docs/proportional-font.md.

Stages
  1. load translation/*.jsonl (empty 'en' = keep the original).  Records are grouped by the source
     path in their id ("FLOW_PRG/MEETING.BIN#3f204" -> "FLOW_PRG/MEETING.BIN"), NOT by file name.
  2. text patchers, chosen by source path:
        FLOW_PRG/*.BIN, ATFIRST/{HELP,TITLE,FACEMDUL}.BIN   tools/textrepack.py (pool repacking, default) or
                                                              tools/textdb.py per-string insertion (--repack off)
        1ST_READ.BIN, 2_DP.BIN                               tools/textfmt_ptrblob.py (in place only unless
                                                              --relocate-ptrblob)
        DPETC/MESSAGE.INI                                    tools/textfmt_ini.py
        ETC_DATA/BPINFO.BIN  (patched into ETC_DATA/ AND ATFIRST/ copies)   tools/textfmt_bpinfo.py
  3. optional extra inputs (all absent = nothing happens)
        translation/font/edit_full.png, edit_half.png    glyph sheets (tools/font.py export) -> both FONT.BIN
        translation/members/<container iso path>/<member name>   replacement member (ZSARC container is
                                                                  rebuilt with new header/CRC, 4-aligned)
        translation/textures/<iso path>/<texture id>.pvr   repainted texture (tools/texinject.py: same pixel format/size,
                                                          container re-laid-out with exact original length by default)
        translation/files/<iso path>                     whole-file replacement
        --proportional-font on   proportional half-width advance (tools/fontpatch.py, default OFF until it has been
                                 verified in the emulator): left-aligns the half-width glyphs 0x21-0x7E in both
                                 FONT.BIN copies, writes cave + width table into the 1ST_READ.BIN tail and hooks the
                                 98 overlays' layout function.  Composes on top of every stage above; no file grows.
                                 Optional translation/font/advance.json {"0x41": 12, "A": 12} overrides table entries.
        --money-format on|money-only|off   English money text (tools/moneypatch.py, docs/number-formats.md), default on:
                                 cave at 0x8c299a00 in the 1ST_READ.BIN tail + a 12 byte hook in the money function of 102
                                 overlays (and %D printing ASCII digits).  No file grows.
  4. tools/discbuild.py build_disc (only files whose bytes changed are handed over); capacity guard (stops before LBA 549150
     unless --allow-overflow), optional --dedupe-files on / --add-file, then tools/verify_disc.py on the written image
  5. summary.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import textdb            # noqa: E402
import textrepack        # noqa: E402
import textfmt_common as C   # noqa: E402
import textfmt_ini       # noqa: E402
import textfmt_bpinfo    # noqa: E402
import textfmt_ptrblob as P  # noqa: E402
import bzlib             # noqa: E402
import hwguard           # noqa: E402

HW_ALIGN = 4             # start alignment of a relocated half-width string (s8gf: the first relocation ran at 1 byte, bases landed on odd addresses)
HW_COMPACT = True        # also try the plan that repacks EVERY movable string of an overlay (prop10c did; needs byte packing to fit)
# field classes of refit forms, the first to be given up (back to the in-place short form) when an overlay has no 4-aligned room for all of them
REFIT_DROP_ORDER = ('person', 'other', 'sponsor', 'town', 'city', 'nation', 'jclub', 'club')

EXTRACTED = os.path.join(ROOT, 'extracted')
SURVEY = os.path.join(HERE, 're', 'textengine', 'survey_overlays.tsv')
PTRBLOB_BASE = 0x8C010000
FONT_LIMIT = 0x8ce02000 - 0x8cd5c000     # 679936: FONT.BIN load slot (docs/font.md s6)
BPINFO_COPIES = ('ETC_DATA/BPINFO.BIN', 'ATFIRST/BPINFO.BIN')
FONT_COPIES = ('FONT.BIN', 'ATFIRST/FONT.BIN')


TEXT_KINDS = ('overlay', 'ptrblob', 'ini', 'bpinfo', 'bcast')
BCAST_SOURCE = 'BCAST/BCAST.BIN'          # voice-clip subtitle headers (tools/textfmt_bcast.py, docs/text-sources.md)
STYLES = ('jp', 'western')       # == moneypatch.STYLES (checked again by moneypatch.make_patches)


class PipelineError(Exception):
    pass


# ------------------------------------------------------------------ helpers
def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def read_extracted(source):
    with open(os.path.join(EXTRACTED, *source.split('/')), 'rb') as f:
        return f.read()


def disc_paths():
    """{UPPER iso path: size} from extracted/_filelist.tsv (path, LBA, size)."""
    out = {}
    with open(os.path.join(EXTRACTED, '_filelist.tsv'), encoding='utf8') as f:
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            if len(p) >= 3 and p[1].isdigit():
                out[p[0].upper()] = int(p[2])
    return out


def load_tdb(tdb):
    """-> {source: [records]}; ids must be unique across all files."""
    by_src = {}
    seen = {}
    for p in sorted(glob.glob(os.path.join(_abs(tdb), '*.jsonl'))):
        with open(p, encoding='utf-8') as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                rid = r['id']
                if rid in seen:
                    raise PipelineError('duplicate id %s in %s and %s' % (rid, seen[rid], os.path.basename(p)))
                seen[rid] = os.path.basename(p)
                by_src.setdefault(rid.rsplit('#', 1)[0], []).append(r)
    return by_src


def apply_refit(by_src, tdb, res=None, relocate=True):
    """--refit on: the names owner's refit overlays (tools/refit.py, translation/refit/*.jsonl) replace the English of existing
    records so that strings get a proper form instead of the slot-forced abbreviation.  API (docs of tools/refit.py):
    `refit.load_overlays(db_by_source, overlay_dir=None, relocate=True, report=None) -> [modified records]`, which changes the DB
    record dicts IN MEMORY (en only; translation/*.jsonl is never written).  The overlay directory is <tdb>/refit.  `relocate` is the
    effective --hw-relocate (on or force): with it off a refit that needs relocation is skipped by refit itself.
    Returns the refit Report (modified / skipped lists); its summary goes into the build notes."""
    try:
        import refit
    except ImportError as e:
        raise PipelineError('--refit on needs tools/refit.py (names owner): %s' % e)
    rep = refit.Report()
    try:
        refit.load_overlays(by_src, os.path.join(_abs(tdb), 'refit'), relocate, rep)
    except ValueError as e:                  # malformed / duplicate overlay record: file:line in the message
        raise PipelineError('refit overlays: %s' % e)
    if res is not None:
        res.notes.append(rep.summary())
        for rid, code, msg in rep.skipped[:10]:
            res.notes.append('  refit skipped %s (%s): %s' % (rid, code, msg))
    return rep


def overlay_sources():
    return {s for s, _ in textdb.list_sources() if s != '1ST_READ.BIN'}


def handler_for(source):
    if source == 'DPETC/MESSAGE.INI':
        return 'ini'
    if source in BPINFO_COPIES:
        return 'bpinfo'
    if source in ('1ST_READ.BIN', '2_DP.BIN'):
        return 'ptrblob'
    if source == BCAST_SOURCE:
        return 'bcast'
    if source in overlay_sources():
        return 'overlay'
    return None


def _hexoff(rid):
    return int(rid.rsplit('#', 1)[1], 16)


def load_survey():
    """{overlay file name: dict(end_var_off, end, cls)} from the textengine agent's survey."""
    out = {}
    if not os.path.exists(SURVEY):
        return out
    with open(SURVEY, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) != len(hdr):
                continue
            d = dict(zip(hdr, p))
            out[d['overlay']] = d
    return out


def append_eligible(source, img, survey):
    """Conflict resolution textengine <-> overlaytext (docs/pipeline.md s5): appending after an overlay is only
    allowed for FLOW_PRG overlays that the survey classed 'no-bss(_end==file end)', where the u32 `_end` word
    inside the image really equals base+size, and never for GAME.BIN (its stub clears a fixed BSS range).
    The caller must raise that `_end` word by the growth.  Returns the offset of the word or None."""
    if not source.startswith('FLOW_PRG/') or source.endswith('/GAME.BIN'):
        return None
    # skeptic review (docs/capacity-design.md s9): these stubs ignore a raised _end or sit off-slot, so appended
    # bytes would land in a private area / unbudgeted memory.  Never append to them.
    if source.split('/')[-1] in ('ESTABLIS.BIN', 'LOADBAR.BIN', 'MOVIE.BIN', 'MOVIE_BG.BIN'):
        return None
    d = survey.get(source.split('/')[-1])
    if not d or not d.get('class', '').startswith('no-bss'):
        return None
    try:
        off = int(d['end_var_off'], 16)
        end = int(d['_end'], 16)
    except (ValueError, KeyError):
        return None
    import struct
    if end != img.base + img.size or off + 4 > img.size:
        return None
    if struct.unpack_from('<I', img.data, off)[0] != end:
        return None
    return off


# Overlays that never get the opt-in BSS-pad growth (--grow-overlays; docs/expansion/overlay-memory.md s3): GAME (its stub zeroes
# [*0x8c4bc88c,_end), which would wipe appended bytes), ESTABLIS / MOVIE / MOVIE_BG / LOADBAR (stub ignores `_end`, private areas),
# and the overlays whose base is not slot aligned / has no scene record (COMM CON_REP NF_CON PASS_PL J1_REP PL_CON: budget 0 there).
GROW_EXCLUDE = frozenset(('GAME.BIN', 'ESTABLIS.BIN', 'LOADBAR.BIN', 'MOVIE.BIN', 'MOVIE_BG.BIN',
                          'COMM.BIN', 'CON_REP.BIN', 'NF_CON.BIN', 'PASS_PL.BIN', 'J1_REP.BIN', 'PL_CON.BIN'))
GROW_CAPS = {'HELP.BIN': 20480}      # HELP: slot 11 is resident right behind it (measured free 48,320 B, policy 20,480 B)
GROW_MAX = 262144                    # largest N accepted by --grow-overlays (the smallest 'safe growth' of the study's table is 20 KiB,
                                     # most overlays have 120-220 KiB; the heap of every overlay with BSS is >= 0.97 MB)


def grow_plan(source, img, survey, grow):
    """Opt-in `--grow-overlays N` (docs/expansion/overlay-memory.md s0 item 4 / s8 option 1): the SAFEST form, an overlay WITH a BSS
    area may get appended text behind a zero pad up to its old `_end` (so every BSS address keeps meaning what the code expects),
    and the `_end` word is raised by pad + growth (heap start = round32(_end)+0x20 moves up by exactly that).  INFERRED, never booted.
    Returns (offset of the `_end` word, old `_end` address, max growth in bytes) or None when not eligible: not a FLOW_PRG overlay, in
    GROW_EXCLUDE, not class 'bss' in the survey, `_end` word not found at the survey's offset / not equal to the survey `_end`
    / below the image end."""
    if grow <= 0 or not source.startswith('FLOW_PRG/'):
        return None
    name = source.split('/')[-1]
    if name in GROW_EXCLUDE:
        return None
    d = survey.get(name)
    if not d or d.get('class') != 'bss':
        return None
    try:
        off = int(d['end_var_off'], 16)
        end = int(d['_end'], 16)
    except (ValueError, KeyError):
        return None
    import struct
    if end < img.base + img.size or off + 4 > img.size or struct.unpack_from('<I', img.data, off)[0] != end:
        return None
    return off, end, min(grow, GROW_CAPS.get(name, GROW_MAX))


# ------------------------------------------------------------------ result
class FileReport:
    def __init__(self, iso, kind):
        self.iso, self.kind = iso, kind
        self.old_size = self.new_size = 0
        self.records = self.with_en = self.applied = 0
        self.in_place = self.relocated = self.appended = 0
        self.failed = []     # (id, reason)
        self.skipped = []    # (id, reason)
        self.notes = []
        self.changed = False


class Result:
    def __init__(self):
        self.patches = {}       # iso path -> bytes (only changed files)
        self.sparse = {}        # iso path -> {byte offset: bytes}: in-place sector edits of a file that is not replaced whole (BCAST.BIN)
        self.files = []         # FileReport
        self.total_records = 0
        self.total_with_en = 0
        self.unknown_sources = {}
        self.notes = []
        self.disc = None
        self.refit = None           # refit.Report of --refit on (before / cls of every modified record)
        self.refit_reverted = []    # ids of refit forms given up by hw_relocate_fit

    def totals(self):
        t = dict(records=self.total_records, with_en=self.total_with_en,
                 applied=sum(f.applied for f in self.files if f.kind in TEXT_KINDS),
                 failed=sum(len(f.failed) for f in self.files),
                 skipped=sum(len(f.skipped) for f in self.files),
                 in_place=sum(f.in_place for f in self.files),
                 relocated=sum(f.relocated for f in self.files),
                 appended=sum(f.appended for f in self.files),
                 files_changed=len(self.patches) + len(self.sparse),
                 growth=sum(f.new_size - f.old_size for f in self.files if f.changed))
        t['untranslated'] = t['records'] - t['applied']
        t['asset_files'] = sum(1 for f in self.files if f.kind not in TEXT_KINDS and f.changed)
        return t


def _put(res, iso, data, rep, old):
    """register a patched file (skip if byte-identical to the original)."""
    if iso in res.patches:
        raise PipelineError('file %s produced by two pipeline stages' % iso)
    rep.old_size, rep.new_size = len(old), len(data)
    if bytes(data) != old:
        res.patches[iso] = bytes(data)
        rep.changed = True


# ------------------------------------------------------------------ text handlers
def overlap_false_positives(strs, ptrs):
    """Offsets of extracted 'strings' whose region [off, off+max_bytes) overlaps an aligned pointer word that references
    another extracted string (not one of their own referencing words): pointer data read as text by tools/textdb.py (1 string in the
    whole game today: FLOW_PRG/NEWS_OP.BIN#28f21, tools/re/capacity/synth/ptroverlap.py).  Writing English into them would clobber that pointer, and repacking would
    move the table, so they are never touched (reported as failed)."""
    import bisect
    refwords = {w for s in strs for w in s.refs}      # words that really point at an extracted string
    words = sorted(w for w in ptrs if w in refwords)
    bad = {}
    for s in strs:
        own = set(s.refs)
        i = bisect.bisect_left(words, s.off - 3)
        while i < len(words) and words[i] < s.off + s.max_bytes:
            w = words[i]
            if w + 4 > s.off and w not in own:
                bad[s.off] = w
                break
            i += 1
    return bad


def _legacy_overlay(img, recs, source, survey, append_safe, rep, extracted=None, grow=0):
    """textdb.insert_image (per string, relocation inside freed regions) + optional append-safe.
    grow > 0 (--grow-overlays N, needs append_safe): overlays with a BSS area may also take up to N appended bytes (grow_plan).
    Returns (new bytes, InsertReport with in_place/relocated/appended/failed/skipped/translated)."""
    old = img.data
    new, r = textdb.insert_image(img, recs, append=False, extracted=extracted)
    if r.failed and append_safe:
        off = append_eligible(source, img, survey)
        gp = grow_plan(source, img, survey, grow) if off is None else None
        if gp is not None:
            import struct
            goff, gend, cap = gp
            padded = textdb.Image(img.source, img.data + bytes(((gend - img.base + 3) & ~3) - img.size), img.base)
            new2, r2 = textdb.insert_image(padded, recs, append=True, extracted=extracted)
            growth = len(new2) - padded.size
            if growth > cap:
                rep.notes.append('grow-overlays: %s needs %d appended bytes, limit %d: left as repacked' % (source, growth, cap))
            elif growth > 0 and not r2.failed:
                new2 = bytearray(new2)
                struct.pack_into('<I', new2, goff, img.base + len(new2))     # `_end` raised by pad + growth
                new, r = bytes(new2), r2
                rep.notes.append('grow-overlays: zero pad %d bytes up to the old `_end` %#x, +%d bytes appended, `_end` word @%#x '
                                 'raised to %#x (file +%d bytes; INFERRED, never booted)' % (
                                     padded.size - img.size, gend, growth, goff, img.base + len(new), len(new) - len(old)))
        elif off is not None:
            new2, r2 = textdb.insert_image(img, recs, append=True, extracted=extracted)
            if len(new2) > len(old) and not r2.failed:
                import struct
                new2 = bytearray(new2)
                struct.pack_into('<I', new2, off, img.base + len(new2))      # raise `_end` with the growth
                new, r = bytes(new2), r2
                rep.notes.append('append-safe: +%d bytes, `_end` word @%#x raised to %#x' % (
                    len(new) - len(old), off, img.base + len(new)))
        else:
            rep.notes.append('append-safe requested but %s is not eligible (BSS / unknown `_end`)' % source)
    return new, r


_JUNK_EN = {'-', 'Plot', 'Misc', 'Bow'}


def is_junk_orphan(r):
    """orphan record whose English is a placeholder (tools/re/int_blankjunk.py blanks them in the database; this is the safety net)."""
    en = (r.get('en') or '').strip()
    return bool(r.get('orphan') and en and (en in _JUNK_EN or all(c in '-_.?*/ ' for c in en)))


def is_binary_record(r, img):
    """Record (orphan or not) whose ORIGINAL bytes are machine data that the extractor read as cp932 text: a pointer, a
    struct or SH-4 code.  Writing English over it breaks the game; docs/hang-investigation.md s9: `---` over
    FLOW_PRG/GAME.BIN#82138 (a script pointer that 3,502 name-table entries use) reset the console when a goal was scored.
    is_junk_orphan cannot see these because they are pointer records, so this test reads the original bytes:
      R1  English without any ASCII letter or digit (`-`, `---`, `?`) over an original that contains a kanji.  A genuine
          punctuation record (a full-width dash, `...` for an ellipsis, `->` for an arrow) has no kanji, which is what separates them.
      R2  the original starts with, or holds, two or more consecutive 4-aligned words that point into this image: a
          pointer table with a string glued behind it, overwritten with real English (the week-label table of AUTOSAVE).
          One in-image word alone is not enough (`8c d6 93 8c` is a two-character place name), nor is the top byte alone
          (0x8c is a Shift-JIS lead byte).
    Measured over all 396,819 records with English of the database: 17 records, no genuine text among them (tools/test_junk.py)."""
    en = (r.get('en') or '').strip()
    if not en:
        return False
    off = _hexoff(r['id'])
    d = img.data
    if off >= len(d):
        return False
    e = d.find(b'\0', off)
    raw = d[off:len(d) if e < 0 else e]
    if not any(c.isascii() and c.isalnum() for c in en):                                        # R1
        if any('\u4e00' <= c <= '\u9fff' for c in raw.decode('cp932', errors='replace')):
            return True
    run = 0
    for i in range((-(img.base + off)) % 4, len(raw) - 3, 4):                                    # R2
        w = int.from_bytes(raw[i:i + 4], 'little')
        run = run + 1 if img.base <= w < img.base + len(d) else 0
        if run >= 2:
            return True
    return False


def do_overlay(res, source, recs, survey, append_safe, repack=True, share='none', cross_pool=True, grow=0):
    iso = '/' + source
    rep = FileReport(iso, 'overlay')
    rep.records = len(recs)
    rep.with_en = sum(1 for r in recs if r.get('en'))
    img = textdb.load_image(source)
    old = img.data
    extracted = textdb.extract_image(img)
    fp = overlap_false_positives(extracted[0], extracted[1])
    guarded = []
    if fp:
        guarded = [(r['id'], 'extraction false positive: region overlaps pointer word @%#x (pointer table read as text); left Japanese' % fp[_hexoff(r['id'])])
                   for r in recs if r.get('en') and _hexoff(r['id']) in fp]
        recs = [r for r in recs if not (r.get('en') and _hexoff(r['id']) in fp)]
        extracted = ([s for s in extracted[0] if s.off not in fp], extracted[1], extracted[2])
    junk = [r for r in recs if is_junk_orphan(r)]
    if junk:
        # an orphan record with placeholder English is binary data / code decoded as cp932 (docs/hang-investigation.md s0): never write it
        guarded += [(r['id'], 'junk orphan record (placeholder English over binary data or code); left unchanged') for r in junk]
        ids = {r['id'] for r in junk}
        recs = [r for r in recs if r['id'] not in ids]
    binrec = [r for r in recs if is_binary_record(r, img)]
    if binrec:
        # a pointer record whose original bytes are a pointer / struct / code (docs/hang-investigation.md s9): never write it
        guarded += [(r['id'], 'binary record (pointer table, data or code read as text); left unchanged') for r in binrec]
        ids = {r['id'] for r in binrec}
        recs = [r for r in recs if r['id'] not in ids]
    if not repack:
        new, r = _legacy_overlay(img, recs, source, survey, append_safe, rep, extracted, grow)
        rep.in_place, rep.relocated, rep.appended = r.in_place, r.relocated, r.appended
        rep.failed = guarded + [(f[0], f[2] if len(f) > 2 else '') for f in r.failed]
        rep.skipped = list(r.skipped)
        rep.applied = r.translated - len(r.failed)
        _put(res, iso, new, rep, old)
        res.files.append(rep)
        return
    # ---- layer 1 (docs/capacity-design.md): pool repacking.  Strings stay inside their original pool
    # ranges, the image size never changes, only pool bytes and pointer words change.
    rr = textrepack.Report(source)
    by_off = {s.off: s for s in extracted[0]}
    enc = textrepack._entry_enc(recs, by_off, rr, source)
    new, rp = textrepack.repack(old, img.base, recs, source=source, share=share, cross_pool=cross_pool,
                                extracted=extracted)
    if rp.translated:
        bad = textrepack.check(old, new, img.base, extracted[0], enc, rp, share=share)
        if bad:
            raise PipelineError('%s: repack self-check failed: %s' % (source, '; '.join(bad[:5])))
    failed = [(o['id'], 'pool full: needs %d bytes, original %d (pool deficit %d before moves); stays Japanese' % (
        o['need'], o['orig'], o['pool_deficit'])) for o in rp.overflow]
    failed += [(o['id'], 'does not fit in place (%d > %d) and cannot be relocated (%s)' % (o['need'], o['have'], o['reason']))
               for o in rp.fixed_overflow]
    if failed and append_safe:        # opt-in legacy fallback for no-BSS overlays (INFERRED, never run in-game)
        n_before = len(failed)
        nl, r2 = _legacy_overlay(img, recs, source, survey, True, rep, extracted, grow)
        if len(nl) > len(old) and not r2.failed:
            rep.in_place, rep.relocated, rep.appended = r2.in_place, r2.relocated, r2.appended
            rep.skipped = list(r2.skipped)
            rep.applied = r2.translated
            rep.notes.append('repack left %d strings Japanese; append-safe fallback housed all of them' % n_before)
            _put(res, iso, nl, rep, old)
            res.files.append(rep)
            return
    placed = rp.translated - len(rp.overflow) - len(rp.fixed_overflow)
    moved = sum(1 for o, n_ in rp.layout.items() if o != n_)
    if placed == 0:
        new = old          # nothing could be placed: do not keep cross-pool moves made while trying (image stays original)
        rep.notes.append('repack: no string placed, overlay left untouched')
    rep.relocated = min(moved, placed) if placed else 0
    rep.in_place = placed - rep.relocated
    rep.failed = guarded + failed
    rep.skipped = list(rp.skipped)
    rep.applied = placed
    if rp.moved or rp.shared_saved or rp.repacked_pools:
        rep.notes.append('repack: %d pools rewritten, %d strings moved between pools, %d bytes saved by sharing' % (
            rp.repacked_pools, rp.moved, rp.shared_saved))
    _put(res, iso, new, rep, old)
    res.files.append(rep)


def _cstr_ja(data, off):
    if not 0 <= off < len(data):
        return None
    e = data.find(b'\0', off)
    if e < 0:
        return None
    try:
        return C.decode_text(data[off:e])
    except Exception:
        return None


def do_ptrblob(res, source, recs, relocate):
    iso = '/' + source
    rep = FileReport(iso, 'ptrblob')
    rep.records = len(recs)
    rep.with_en = sum(1 for r in recs if r.get('en'))
    data = read_extracted(source)
    ok = []
    for r in recs:
        if not r.get('en'):
            continue
        off = _hexoff(r['id'])
        if _cstr_ja(data, off) != r['ja']:
            rep.skipped.append((r['id'], 'ja text differs from image (stale database?)'))
            continue
        try:
            b = C.encode_text(r['en']) + b'\0'
        except (UnicodeEncodeError, ValueError) as ex:
            rep.skipped.append((r['id'], 'unencodable: %s' % ex))
            continue
        cap = r.get('max_bytes')
        if cap is not None and len(b) <= cap:
            rep.in_place += 1
            ok.append(r)
        elif relocate and r.get('refs') and cap is not None:
            rep.relocated += 1
            ok.append(r)
        else:
            rep.failed.append((r['id'], 'does not fit in place (%d > %s) and relocation is off/impossible' % (len(b), cap)))
    new = P.apply(data, ok, PTRBLOB_BASE, relocate=relocate) if ok else data
    rep.applied = len(ok)
    _put(res, iso, new, rep, data)
    res.files.append(rep)


def do_ini(res, source, recs):
    iso = '/' + source
    rep = FileReport(iso, 'ini')
    rep.records = len(recs)
    rep.with_en = sum(1 for r in recs if r.get('en'))
    data = read_extracted(source)
    cur = {e['id']: e['ja'] for e in textfmt_ini.extract(data)}
    ok = []
    for r in recs:
        if not r.get('en'):
            continue
        if cur.get(r['id']) != r['ja']:
            rep.skipped.append((r['id'], 'ja text differs from file (stale database?)'))
            continue
        try:
            C.encode_text(r['en'])
        except (UnicodeEncodeError, ValueError) as ex:
            rep.skipped.append((r['id'], 'unencodable: %s' % ex))
            continue
        ok.append(r)
    new = textfmt_ini.apply(data, ok) if ok else data
    rep.applied = rep.in_place = len(ok)
    _put(res, iso, new, rep, data)
    res.files.append(rep)


BCAST_LEAD_GLUE = ",.;:!?)]}'"      # first characters that continue the previous clip's sentence: no blank in front of them (", isn't it?", "'s play", ")")


def bcast_clip_text(en, ctx, lead_space):
    """The text written for one subtitle segment.  Clips of one utterance are drawn one behind the other without a separator, the Japanese needs none, English does.
    lead_space (--clip-lead-space on, needs --cell-prop on): ONE blank in FRONT of every clip whose English starts with a letter, digit or opening quote / bracket / asterisk
    (player names and team names included: they follow `The one to watch,` / `Seoul FC vs`), none in front of a clip that starts with `, . ; : ! ? ) ] } '`; nothing is appended,
    so a name or a team name is never followed by a stray blank (`Grampus, ...`, `Suzuki's ...`).  The blank at the first column of a line is skipped by the --cell-prop engine
    (first clip of an utterance, line start after a wrap).  Off: the old rule, ONE trailing blank after every clip except name callouts (folder `name`)."""
    if lead_space:
        return en if en[:1] == ' ' or en[:1] in BCAST_LEAD_GLUE else ' ' + en
    if not ctx.startswith('clip name\\') and not en.endswith(' '):
        return en + ' '        # clips played one after the other are shown one behind the other: the Japanese needs no gap, English does
    return en


def do_bcast(res, source, recs, lead_space=False):
    """/BCAST/BCAST.BIN voice clips: the subtitle segments of the 2048-byte clip headers (tools/textfmt_bcast.py).  The headers are read from
    the ORIGINAL disc, edited (in place, or the clip re-laid out inside its header sector) and handed to discbuild as sparse sector edits:
    the 630 MB archive is never held in memory and nothing moves.  lead_space: see bcast_clip_text."""
    import gdrom
    import textfmt_bcast as B
    iso = '/' + source
    rep = FileReport(iso, 'bcast')
    rep.records = len(recs)
    rep.with_en = sum(1 for r in recs if r.get('en'))
    by_sector = {}
    for r in recs:
        if not r.get('en'):
            continue
        off = _hexoff(r['id'])
        en = bcast_clip_text(r['en'], r.get('ctx', ''), lead_space)
        by_sector.setdefault(off // B.SECTOR, {})[off % B.SECTOR] = (r['id'], r['ja'], en, r.get('max_bytes'))
    disc = gdrom.Disc(ROOT)
    edits = {}
    relaid = 0
    for sec in sorted(by_sector):
        if sec >= B.BCAST_SECTORS:
            for rid, ja, en, cap in by_sector[sec].values():
                rep.skipped.append((rid, 'offset beyond the end of BCAST.BIN'))
            continue
        h = B.read_header(disc, sec)
        if h[:16] != B.MAGIC:
            for rid, ja, en, cap in by_sector[sec].values():
                rep.skipped.append((rid, 'no clip header at this sector (stale database?)'))
            continue
        todo = {o: (ja, en, cap) for o, (rid, ja, en, cap) in by_sector[sec].items()}
        new, bad, stale = B.apply_to_header(h, todo)
        for o, why in stale:
            rep.skipped.append((by_sector[sec][o][0], why))
        for o, why in bad:
            rep.failed.append((by_sector[sec][o][0], why))
        n_ok = len(todo) - len(bad) - len(stale)
        rep.applied += n_ok
        if new != h:
            edits[sec * B.SECTOR] = new
            if new[B.TABLE:B.TEXT0] != h[B.TABLE:B.TEXT0]:
                relaid += 1
    rep.in_place = rep.applied - relaid
    rep.relocated = relaid
    rep.notes.append('clip separator: %s' % ('one LEADING blank per clip that starts with a letter / digit / opening mark (--clip-lead-space, the --cell-prop engine skips a blank at column 0)'
                                             if lead_space else 'one TRAILING blank after every clip except name callouts (old rule; --clip-lead-space off)'))
    if relaid:
        rep.notes.append('%d clip(s) re-laid out inside their header sector (English longer than the Japanese slots)' % relaid)
    rep.changed = bool(edits)
    if edits:
        if iso in res.sparse:
            raise PipelineError('file %s produced by two pipeline stages' % iso)
        res.sparse[iso] = edits
    res.files.append(rep)


def do_bpinfo(res, recs_by_src):
    """One DB (either source id) patches BOTH BPINFO copies (identical name fields)."""
    recs = []
    for s in BPINFO_COPIES:
        recs += recs_by_src.get(s, [])
    seen = {}
    for r in recs:
        off = _hexoff(r['id'])
        if off in seen and seen[off].get('en') != r.get('en'):
            raise PipelineError('conflicting BPINFO translations for offset %#x' % off)
        seen[off] = r
    recs = list(seen.values())
    for copy in BPINFO_COPIES:
        iso = '/' + copy
        rep = FileReport(iso, 'bpinfo')
        rep.records = len(recs)
        rep.with_en = sum(1 for r in recs if r.get('en'))
        data = read_extracted(copy)
        cur = {_hexoff(e['id']): e['ja'] for e in textfmt_bpinfo.extract(data, copy)}
        ok = []
        for r in recs:
            if not r.get('en'):
                continue
            if cur.get(_hexoff(r['id'])) != r['ja']:
                rep.skipped.append((r['id'], 'ja name differs from file (stale database?)'))
                continue
            try:
                n = len(C.encode_text(r['en']))
            except (UnicodeEncodeError, ValueError) as ex:
                rep.skipped.append((r['id'], 'unencodable: %s' % ex))
                continue
            if n > textfmt_bpinfo.NAME - 1:
                rep.failed.append((r['id'], 'name is %d bytes, max %d' % (n, textfmt_bpinfo.NAME - 1)))
                continue
            ok.append(r)
        new = textfmt_bpinfo.apply(data, ok) if ok else data
        if copy != BPINFO_COPIES[0]:      # the two copies share one DB: count its strings only once
            rep.notes.append('same names as %s (counted there)' % BPINFO_COPIES[0])
            rep.failed, rep.records, rep.with_en = [], 0, 0
        else:
            rep.applied = rep.in_place = len(ok)
        _put(res, iso, new, rep, data)
        res.files.append(rep)


# ------------------------------------------------------------------ font hook
def apply_font(res, font_dir):
    """translation/font/edit_full.png and/or edit_half.png: sheets as written by `tools/font.py export`
    (edited).  The glyphs that differ from the ORIGINAL root FONT.BIN are applied to each FONT.BIN copy
    (the copies differ in glyph 3580, which an unedited sheet must not touch)."""
    full = os.path.join(font_dir, 'edit_full.png')
    half = os.path.join(font_dir, 'edit_half.png')
    have_full, have_half = os.path.exists(full), os.path.exists(half)
    if not (have_full or have_half):
        return
    import font as F
    base_data = read_extracted(FONT_COPIES[0])
    base = F.Font(base_data)
    edit = F.Font(base_data)
    nf = F.import_edit_sheet(edit, full) if have_full else 0
    nh = F.import_edit_sheet(edit, half, half=True) if have_half else 0
    chg_full = [i for i in range(len(base.glyphs)) if edit.glyphs[i] != base.glyphs[i]]
    bh, eh = base.half(), edit.half()
    chg_half = [i for i in range(len(bh)) if bh[i] != eh[i]]
    assert len(chg_full) == nf and len(chg_half) == nh
    for copy in FONT_COPIES:
        iso = '/' + copy
        rep = FileReport(iso, 'font')
        old = read_extracted(copy)
        f = F.Font(old)
        for i in chg_full:
            f.set_glyph(i, edit.glyphs[i])
        for i in chg_half:
            f.set_half(i, eh[i])
        new = f.build() if (chg_full or chg_half) else old
        if len(new) > FONT_LIMIT:
            raise PipelineError('%s is %d bytes, above the %d byte FONT.BIN load slot' % (copy, len(new), FONT_LIMIT))
        rep.records = rep.with_en = rep.applied = len(chg_full) + len(chg_half)
        rep.notes.append('%d full-width + %d half-width glyphs replaced' % (len(chg_full), len(chg_half)))
        _put(res, iso, new, rep, old)
        res.files.append(rep)


# ------------------------------------------------------------------ containers / whole files
def patch_container(data, repl):
    """Replace members of a bare ZSARC container (tools/bzlib.py).  repl {member name: new plaintext}.
    Unchanged members are copied byte for byte; changed members are re-encoded with their original method,
    name, mtime and extension layout (new sizes, CRC16 and header CRC), followed by zero padding to 4 bytes.
    The container must be a plain concatenation of members (parse_archive consumes the whole file)."""
    members, tail = bzlib.parse_archive(data)
    if tail != len(data) or not members:
        raise PipelineError('not a plain ZSARC container (parsed %d members, stopped at %#x of %#x)' % (
            len(members), tail, len(data)))
    names = [m.name for m in members]
    unknown = [n for n in repl if n not in names]
    if unknown:
        raise PipelineError('no such member(s) %s (have e.g. %s)' % (unknown, names[:5]))
    dup = [n for n in repl if names.count(n) > 1]
    if dup:
        raise PipelineError('ambiguous member name(s) %s' % dup)
    out = bytearray()
    pos = 0
    prev_replaced = False
    for m in members:
        if not prev_replaced:
            out += data[pos:m.offset]          # original zero padding / alignment
        while len(out) % 4:
            out.append(0)
        if m.name in repl:
            out += bzlib.member_record(m, bytes(repl[m.name]))
            prev_replaced = True
        else:
            out += data[m.offset:m.end_offset]
            prev_replaced = False
        pos = m.end_offset
    out += data[pos:]
    out = bytes(out)
    # verify by re-parsing
    m2, t2 = bzlib.parse_archive(out)
    if t2 != len(out) or [m.name for m in m2] != names:
        raise PipelineError('re-parse of patched container failed')
    for a, b in zip(members, m2):
        if a.name in repl:
            if b.extract() != bytes(repl[a.name]) or b.hdr_crc_ok is False:
                raise PipelineError('member %s did not round-trip' % a.name)
        elif a.packed != b.packed or a.header != b.header:
            raise PipelineError('untouched member %s changed' % a.name)
    return out


def _split_container(rel_parts):
    """longest leading part of a path under translation/members that is an extracted file."""
    for i in range(len(rel_parts) - 1, 0, -1):
        cand = '/'.join(rel_parts[:i])
        if os.path.isfile(os.path.join(EXTRACTED, *rel_parts[:i])):
            return cand, '/'.join(rel_parts[i:])
    raise PipelineError('translation/members/%s: no container file in extracted/ matches' % '/'.join(rel_parts))


def apply_members(res, members_dir):
    if not os.path.isdir(members_dir):
        return
    groups = {}
    for dp, _, fns in os.walk(members_dir):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, members_dir).replace(os.sep, '/').split('/')
            cont, member = _split_container(rel)
            with open(full, 'rb') as fh:
                groups.setdefault(cont, {})[member] = fh.read()
    for cont in sorted(groups):
        iso = '/' + cont
        rep = FileReport(iso, 'container')
        old = read_extracted(cont)
        new = patch_container(old, groups[cont])
        rep.records = rep.with_en = rep.applied = len(groups[cont])
        rep.notes.append('members replaced: %s' % ', '.join(sorted(groups[cont])))
        _put(res, iso, new, rep, old)
        res.files.append(rep)


def apply_textures(res, textures_dir, policy='exact'):
    """translation/textures/<iso path>/<texture id>.pvr -> tools/texinject.py (docs/texture-injection.md).
    Composes on the CURRENT bytes of the file (an earlier stage may already have patched it), so it must run after the
    text stages.  policy 'exact' keeps every file length (FitError -> PipelineError naming the texture)."""
    if not textures_dir or not os.path.isdir(textures_dir):
        return
    import texinject
    try:
        groups = texinject.load_textures_dir(textures_dir, EXTRACTED)
    except texinject.TexInjectError as e:
        raise PipelineError('textures: %s' % e)
    problems = []        # (file, texture id, message): every offender is listed in ONE error, not just the first
    for cont in sorted(groups):
        iso = '/' + cont
        rep = FileReport(iso, 'texture')
        old = read_extracted(cont)
        cur = res.patches.get(iso, old)
        new, infos = cur, []
        for tid in sorted(groups[cont], key=str):
            try:
                r = texinject.inject(new, tid, groups[cont][tid], policy)
            except texinject.FitError as e:
                over = ('%d bytes over the slot' % (e.need - e.have)) if e.need is not None and e.have is not None else 'does not fit'
                problems.append((cont, tid, '%s (%s)' % (e, over)))
                continue
            except texinject.TexInjectError as e:
                problems.append((cont, tid, str(e)))
                continue
            new = r.data
            infos.append(dict(r.info, tid=tid))
        if new != cur and len(new) == len(cur):
            # a table edited in place inside a stored ZSARC member must leave the member's CRC16 / header CRC valid
            # (the game's walker rejects the member otherwise; docs/scdrf-texture-hang.md)
            for off, name in texinject.stale_stored_members(cur, new):
                problems.append((cont, '@%x' % off, 'stored ZSARC member %r: data CRC16 / header CRC stale after injection' % name))
        rep.records = rep.with_en = rep.applied = len(groups[cont])
        rep.old_size, rep.new_size = len(old), len(new)
        rep.notes.append('textures replaced: %s' % ', '.join(sorted(groups[cont])))
        grown = [i for i in infos if i.get('grown_by')]
        if grown:
            rep.notes.append('GREW by %d bytes (policy grow)' % sum(i['grown_by'] for i in grown))
        if new != old:
            res.patches[iso] = new
            rep.changed = True
        res.files.append(rep)
    if problems:
        lines = ['  %s texture %s: %s' % p for p in problems]
        hint = ('simplify the repainted art so it packs into the original slot (fewer colours / flatter areas; fit_check in '
                'tools/texinject.py), or pass --texture-policy grow, which re-lays-out the container and grows the file: '
                'that is INFERRED safe only, never run in-game (docs/texture-injection.md s7), so it is not the default'
                if policy == 'exact' else 'these containers cannot grow (docs/texture-injection.md s7)')
        raise PipelineError('%d texture(s) cannot be injected under --texture-policy %s:\n%s\n  -> %s' % (
            len(problems), policy, '\n'.join(lines), hint))


def apply_files(res, files_dir):
    if not os.path.isdir(files_dir):
        return
    for dp, _, fns in os.walk(files_dir):
        for fn in sorted(fns):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, files_dir).replace(os.sep, '/')
            rep = FileReport('/' + rel, 'file')
            old = read_extracted(rel)
            with open(full, 'rb') as fh:
                new = fh.read()
            rep.records = rep.with_en = rep.applied = 1
            _put(res, '/' + rel, new, rep, old)
            res.files.append(rep)


# ------------------------------------------------------------------ proportional font (code + table + glyph art)
def apply_prop_font(res, font_dir, variants='A', place='tail', glyphs=True, prop_scale=False, align_fix=False, open_font=None, lin_center=False,
                    small_prop=False, cell_prop=False):
    """tools/fontpatch.py: composes on the CURRENT bytes of 1ST_READ.BIN, both FONT.BIN copies and every overlay that links
    the tsString window library (found by exact byte signature, so text repacking / --append-safe do not matter).
    Runs last (after apply_files) so that a whole-file replacement under translation/files is patched too.  No file grows."""
    import fontpatch as FPT
    overrides = None
    ap = os.path.join(font_dir, 'advance.json')
    if os.path.exists(ap):
        with open(ap, encoding='utf8') as f:
            overrides = FPT.parse_overrides(json.load(f))
    expect = {'A': 98}
    if 'B' in variants:
        expect['B'] = 6
    if 'C' in variants:
        expect['C'] = 1
    try:
        out, rep = FPT.make_patches(read_extracted, current=res.patches, variants=variants, place=place,
                                    overrides=overrides, expect=expect, glyphs=glyphs, prop_scale=prop_scale, align_fix=align_fix,
                                    open_font=open_font, lin_center=lin_center, small_prop=small_prop, cell_prop=cell_prop)
    except FPT.FontPatchError as e:
        raise PipelineError('proportional font: %s' % e)
    for iso in sorted(out):
        new = out[iso]
        r = FileReport(iso, 'propfont')
        r.old_size = r.new_size = len(new)          # always same size: growth of an earlier stage is counted there
        r.changed = True
        r.records = r.with_en = r.applied = 1
        if iso == '/1ST_READ.BIN':
            r.notes.append('cave @%#x (%d B%s), advance table @%#x (256 B)' % (
                rep['cave'], FPT.CAVE_SIZE_SCALE if rep.get('prop_scale') else FPT.CAVE_SIZE,
                ', --prop-scale: windows with advance != 24 scale the table by A/24' if rep.get('prop_scale') else '',
                rep['table_addr']))
        elif iso.endswith('FONT.BIN'):
            r.notes.append('half-width glyphs 0x21-0x7E: Roboto Condensed Medium, OFL-1.1 (--open-font on)' if open_font is not None
                           else 'half-width glyphs 0x21-0x7E (not digits) left-aligned')
        else:
            r.notes.append('tsString layout function hooked (advance + wrap)')
            if align_fix and any(iso.endswith('/' + n[0].split('/')[-1]) or iso.endswith(n[0]) for n in rep.get('panel', ())):
                r.notes.append('align fix: player-card panel strlen -> pw3, 20 x shll2 -> nop (docs/layout-issues.md s10.3)')
        res.patches[iso] = bytes(new)
        res.files.append(r)
    if cell_prop:
        import layoutpatch as LP
        try:
            cout = LP.cell_patches(read_extracted, res.patches, rep['cell'], rep['cell_space'])
        except LP.LayoutPatchError as e:
            raise PipelineError('cell prop: %s' % e)
        for iso, new in sorted(cout.items()):
            r = FileReport(iso, 'layout')
            r.old_size = r.new_size = len(new)
            r.changed = True
            r.records = r.with_en = r.applied = 1
            r.notes.append('commentary subtitle line engine: proportional half-width advance via cell_adv @%#x, blank advance %d px, no blank at column 0 (docs/layout-issues.md s19)' % (
                rep['cell'], rep['cell_space']))
            res.patches[iso] = bytes(new)
            res.files.append(r)
        res.notes.append('cell-prop: commentary subtitle glyphs advance by the proportional table (cave %#x, blank %d px, leading blank after a wrap dropped)' % (
            rep['cell'], rep['cell_space']))
    if lin_center:
        res.notes.append('lin-center: narrow glyphs of the linear text writer (match intro, in-match OPTIONS ...) centred in their 12 px tile (cave %#x, hook %#x)' % (
            rep['lin'], FPT.LIN_SITE + FPT.IMG_BASE))
    if small_prop:
        res.notes.append('small-prop: the 16 px windows of %s get the proportional advance scaled by 2/3 (entry %#x in the font cave tail)' % (
            ', '.join(n.split('/')[-1] for n in rep['small']), FPT.small_entry((rep['cave'], rep['table_addr']))))
    if align_fix:
        res.notes.append('align fix: blank-run columns snap to the cell grid (cave %#x), player-card panel in %s, pw3 %#x' % (
            rep['align'], ', '.join(n[0] for n in rep['panel']), rep['pw3']))
    res.notes.append('proportional font: %d overlays hooked %s, cave %#x, table %#x, mean ASCII advance %.2f px' % (
        sum(rep['sites'].values()), rep['sites'], rep['cave'], rep['table_addr'],
        sum(rep['table'][b] for b in range(0x21, 0x7F)) / 94))


# ------------------------------------------------------------------ layout code fixes (docs/layout-issues.md)
LAYOUT_OPTS = {'guard': True, 'dot': True}     # --club-guard / --club-dot (layoutpatch.make_patches guard / dot)


def apply_layout_patches(res):
    """tools/layoutpatch.py: same-size code fixes that English text needs.  Only applied to an overlay that already carries
    English (it is in res.patches): HOMETOWN.BIN's list-label spacer would cut 4- and 6-letter English words into pairs."""
    import layoutpatch as LP
    if LP.HOMETOWN_ISO not in res.patches:
        return
    try:
        out = LP.make_patches(read_extracted, res.patches, guard=LAYOUT_OPTS['guard'], dot=LAYOUT_OPTS['dot'])
    except LP.LayoutPatchError as e:
        raise PipelineError('layout patch: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 1
        if iso == LP.HOMETOWN_ISO:
            rep.notes.append('HOMETOWN list-label spacer disabled (no letter-pair justification of 4/6-byte words)')
        if LAYOUT_OPTS['guard']:
            rep.notes.append('club-name composer bounded to 13 chars + NUL (town cut to a dotted prefix%s; docs/layout-issues.md s9)'
                             % ('' if LAYOUT_OPTS['dot'] else ', no dot'))
        res.patches[iso] = bytes(new)
        res.files.append(rep)


# ------------------------------------------------------------------ short-name tags (docs/s7t-proposals.md section 2)
def apply_tag_fix(res):
    """tools/layoutpatch.py tag_patches: the shared short_name() routine of 11 overlays (Practice > Player Placement tags and ten more
    name labels) shows the LAST word of the name (up to TAG_LIMIT letters; LP.TAG_LIMIT_BY_OVERLAY: 5 for GAME and TRAINING, 7 for the other nine) instead of the first 4 letters of the given name
    (`Taiy`, `Keij`, `H.`).  Same size, located by signature in the CURRENT bytes (text repacking is kept); a foreign or already
    patched image stops the build."""
    import layoutpatch as LP
    try:
        out = LP.tag_patches(read_extracted, res.patches)
    except LP.LayoutPatchError as e:
        raise PipelineError('tag fix: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 1
        rep.notes.append('short-name tag routine: last name word, up to %d letters (docs/s7t-proposals.md s2)' % LP.tag_limit_for(os.path.basename(iso)[:-4]))
        res.patches[iso] = bytes(new)
        res.files.append(rep)
    res.notes.append('tag fix: short_name() of %d overlays replaced, last word up to %d letters (%s: %d)' % (
        len(out), LP.TAG_LIMIT, ', '.join(sorted(LP.TAG_LIMIT_BY_OVERLAY)), min(LP.TAG_LIMIT_BY_OVERLAY.values())))


# ------------------------------------------------------------------ scout panel Age row (docs/layout-issues.md section 11)
def apply_scout_fix(res):
    """tools/layoutpatch.py scout_patches: the Age row of the scout info panel (SCDRF, SEARCH) starts 2 bytes earlier so that 'Age 25' + NUL
    no longer overwrites its own digits (two halfwords per overlay, signature located, refuses foreign or already patched bytes)."""
    import layoutpatch as LP
    try:
        out = LP.scout_patches(read_extracted, res.patches)
    except LP.LayoutPatchError as e:
        raise PipelineError('scout fix: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 1
        rep.notes.append('scout panel Age row: sprintf buffer b+71 -> b+69 (docs/layout-issues.md s11)')
        res.patches[iso] = bytes(new)
        res.files.append(rep)
    res.notes.append('scout fix: Age row of %d overlays' % len(out))


# ------------------------------------------------------------------ Event income table crowd line (docs/layout-issues.md section 13)
def apply_crowd_fix(res):
    """tools/layoutpatch.py crowd_patches: the crowd-row function of FLOW_PRG/G_INCOME.BIN copies its unit strings with hard-coded 2 byte counts
    ('1ma827pp'); 6 halfwords + 2 pool words + 2 strings in the zero padding make it '1man 827ppl' / '0ppl'.  Same size, signature located on the
    CURRENT bytes (the translated unit text is required), refuses foreign or already patched bytes."""
    import layoutpatch as LP
    try:
        out = LP.crowd_patches(read_extracted, res.patches)
    except LP.CrowdUntranslated as e:      # a partial translation database (development build): the Japanese units need the old 2 byte copies
        res.notes.append('crowd fix skipped: %s' % e)
        return
    except LP.LayoutPatchError as e:
        raise PipelineError('crowd fix: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 1
        rep.notes.append("Event income table crowd line: unit copy counts 2 -> 4 / 3 and '0ppl' (docs/layout-issues.md s13)")
        res.patches[iso] = bytes(new)
        res.files.append(rep)
    res.notes.append('crowd fix: G_INCOME crowd line (man / ppl / 0ppl)')


# ------------------------------------------------------------------ in-match OPTIONS panel highlight windows (docs/layout-issues.md section 18)
def apply_options_fix(res):
    """tools/layoutpatch.py options_patches: the selected-option highlight of the in-match OPTIONS panel (FLOW_PRG/GAME.BIN and its copy in ENDING.BIN) is a
    sprite window of fixed character cells fitted to the Japanese full-width values; the 11 sprite records (data, same size) are recomputed from the cells of
    the English option words in the CURRENT value strings (ON / OFF, A / B, Near / Mid / Far).  An image with Japanese values is left alone; foreign or
    already patched records stop the build."""
    import layoutpatch as LP
    try:
        out = LP.options_patches(read_extracted, res.patches)
    except LP.LayoutPatchError as e:
        raise PipelineError('options fix: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 11
        rep.notes.append('OPTIONS panel: 11 highlight sprite windows follow the English option words (docs/layout-issues.md s18)')
        res.patches[iso] = bytes(new)
        res.files.append(rep)
    res.notes.append('options fix: OPTIONS highlight windows of %d overlays' % len(out))


# ------------------------------------------------------------------ commentary subtitle speed (docs/layout-issues.md section 14)
def apply_bcast_speed(res, speed):
    """tools/layoutpatch.py bcast_patches: the commentary box typewriter of FLOW_PRG/GAME.BIN reveals one character per 2.23 ticks; speed 1.7 / 1.9 /
    2.2 reveals 1.67x / 1.94x / 2.23x as fast (two sites, signature located on the CURRENT bytes, refuses foreign or already patched bytes).
    The Event / scout message typewriter is another function and is not touched."""
    import layoutpatch as LP
    if speed == 'off':
        return
    try:
        out = LP.bcast_patches(read_extracted, res.patches, speed)
    except LP.LayoutPatchError as e:
        raise PipelineError('bcast speed: %s' % e)
    for iso, new in sorted(out.items()):
        rep = FileReport(iso, 'layout')
        rep.old_size = rep.new_size = len(new)
        rep.changed = True
        rep.records = rep.with_en = rep.applied = 1
        rep.notes.append('commentary subtitle reveal speed x%s (docs/layout-issues.md s14)' % speed)
        res.patches[iso] = bytes(new)
        res.files.append(rep)
    res.notes.append('bcast speed: commentary subtitles reveal at x%s of the original speed (GAME.BIN, 2 sites)' % speed)


# ------------------------------------------------------------------ English money format (code + 1ST_READ cave)
def apply_money_fmt(res, decimal_d=True, style='jp'):
    """tools/moneypatch.py: the tsString `%m` money function of 102 overlays (the original prints 億 / 万円 pieces that no English
    string can replace) is redirected to an ASCII formatter in the 1ST_READ.BIN tail (Y150M, Y1.315bn); with decimal_d the `%D`
    branch of the expander prints ASCII digits instead of full-width ones.  Composes on the CURRENT bytes (signature search),
    runs after apply_files, independent of the proportional font (other cave, other function).  No file grows."""
    import moneypatch as MPT
    try:
        out, rep = MPT.make_patches(read_extracted, current=res.patches, expect=MPT.EXPECTED_SITES, variants='A',
                                    decimal_d=decimal_d, style=style)
    except MPT.MoneyPatchError as e:
        raise PipelineError('money format: %s' % e)
    for iso in sorted(out):
        new = out[iso]
        r = FileReport(iso, 'money')
        r.old_size = r.new_size = len(new)
        r.changed = True
        r.records = r.with_en = r.applied = 1
        if iso == '/1ST_READ.BIN':
            r.notes.append('money formatter @%#x (%d B)' % (rep['cave'], rep['size']))
        else:
            r.notes.append('money function hooked' + (' + %D prints ASCII digits' if decimal_d else ''))
        res.patches[iso] = bytes(new)
        res.files.append(r)
    res.notes.append('money format (%s style): %d overlays hooked %s, formatter %#x (%d bytes), %%D %s' % (
        style, len(rep['files']), rep['sites'], rep['cave'], rep['size'], 'ASCII' if decimal_d else 'full-width (original)'))


def hw_array_heads(recs, others=()):
    """Offsets of hwptr records that are element 0 of a fixed-stride array (tools/hwguard.array_heads: Rule A / B): the pointers to
    such a record address the ARRAY, so the string must never be moved.  Always applied (it used to sit behind S8FT_HEADFIX)."""
    return hwguard.array_heads(recs, others)


def hw_relocate_fit(data, base, recs, refit, **kw):
    """textfmt_hwkana.apply_relocate with a fallback for the refit forms (--refit on).  With 4-byte aligned placement an overlay may not have
    room for every refit form (the pools are used to 90 percent and a string takes ceil((len+1)/4) words).  Order of the fallbacks:
      1. a refit form that cannot be written for a reason of its own (record denied / not shown to be text, suffix pointer) goes back to the
         in-place short form of the database (`refit.before`; it fits its slot);
      2. strings that fail with 'no room': the refit forms of the lowest priority classes (REFIT_DROP_ORDER, longest first) go back to the
         short form until nothing fails (smallest prefix by bisection); club words (the user's decision) are never given up for alignment;
      3. if even that does not fit, the overlay is placed at the next smaller alignment (4 -> 2 -> 1) and step 2 is repeated.
    The records are changed in place (en), so the rest of the build sees what was written.
    -> (Relocation, [reverted record ids], alignment used)"""
    import textfmt_hwkana
    if kw.get('guard') and 'index' not in kw:
        kw['index'] = hwguard.ImageIndex(data, base)
    top = kw.get('align', 1)
    rr = textfmt_hwkana.apply_relocate(data, base, recs, **kw)
    if refit is None:
        return rr, [], top
    byid = {r['id']: r for r in recs}
    rev0 = []
    for _ in range(3):
        bad1 = sorted(i for i, m in rr.failed if not m.startswith('no room') and i in refit.before and byid[i].get('en') != refit.before[i])
        if not bad1:
            break
        for i in bad1:
            byid[i]['en'] = refit.before[i]
        rev0 += bad1
        rr = textfmt_hwkana.apply_relocate(data, base, recs, **kw)

    def bad(x):
        return any(m.startswith('no room') for _i, m in x.failed)
    if not bad(rr):
        return rr, rev0, top
    rank = {c: i for i, c in enumerate(REFIT_DROP_ORDER)}
    ladder = [x for x in (4, 2, 1) if x <= top] or [top]
    for al in ladder:
        kw['align'] = al
        cand = [r for r in recs if r['id'] in refit.before and r.get('en') != refit.before[r['id']]
                and (al == 1 or refit.cls.get(r['id']) != 'club')]
        cand.sort(key=lambda r: (rank.get(refit.cls.get(r['id']), 0), -len(r['en']), r['id']))

        def run(n):
            rev = {r['id'] for r in cand[:n]}
            return textfmt_hwkana.apply_relocate(data, base, [dict(r, en=refit.before[r['id']]) if r['id'] in rev else r for r in recs], **kw)
        x = run(0)
        if not bad(x):
            return x, rev0, al
        full = run(len(cand))
        if bad(full) and al != ladder[-1]:
            continue
        lo, hi, best = 0, len(cand), full           # lo fails, hi is good (or the last resort)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            x = run(mid)
            if bad(x):
                lo = mid
            else:
                hi, best = mid, x
        for r in cand[:hi]:
            r['en'] = refit.before[r['id']]
        return best, rev0 + [r['id'] for r in cand[:hi]], al
    return rr, rev0, top


def do_extra(res, source, recs, hw_relocate='off', share='none', others=()):
    """In-place English for the fmt=hwptr (half-width katakana pointer strings) and fmt=recarr (fixed-stride record-array
    fields) records of one overlay.  Runs on the bytes the pool repacking produced (the regions never overlap: extraction
    excludes every textdb string).  A record is checked against the image (stale `ja` -> SKIPPED) and against its slot
    (`slot`, else `max_bytes`; English + NUL must fit -> else FAILED); nothing moves or grows.
    hw_relocate='on' | 'force' (docs/hw-relocation.md): the pointer-referenced hwptr records go through
    textfmt_hwkana.apply_relocate instead: strings that fit stay in place (byte-identical to 'off'), the others move into
    the freed slots of the same overlay and their pointer words are rewritten; 'force' relocates every string (test hook);
    share='dup' lets identical relocated strings share one copy.  A string that finds no room FAILS, never corrupts."""
    import textfmt_gap
    import textfmt_hwkana
    import textfmt_recarray
    iso = '/' + source
    rep = next((f for f in res.files if f.iso == iso and f.kind == 'overlay'), None)
    fresh = rep is None
    if fresh:
        rep = FileReport(iso, 'overlay')
    orig = read_extracted(source)
    data = res.patches.get(iso, orig)
    rep.records += len(recs)
    rep.with_en += sum(1 for r in recs if r.get('en'))
    by_fmt = {'hwptr': [], 'recarr': [], 'gap': []}
    hw_reloc = []
    heads = hw_array_heads(recs, others) if hw_relocate != 'off' else set()
    if heads:
        rep.notes.append('hw array heads kept in place (never relocated): %d' % len(heads))
    for r in recs:
        if not r.get('en'):
            continue
        if hw_relocate != 'off' and r.get('fmt') == 'hwptr' and _hexoff(r['id']) not in heads:
            hw_reloc.append(r)          # checked (stale / unencodable / budget / slack) by apply_relocate
            continue
        off = _hexoff(r['id'])
        try:
            ja_b = C.encode_text(r['ja'])
            en_b = C.encode_text(r['en'])
        except (UnicodeEncodeError, ValueError) as ex:
            rep.skipped.append((r['id'], 'unencodable: %s' % ex))
            continue
        if r.get('fmt') == 'gap' and r.get('cont'):
            # head of a string that continues into the next record: no NUL behind it (textfmt_gap)
            if data[off:off + len(ja_b)] != ja_b:
                rep.skipped.append((r['id'], 'ja text differs from image (stale database?)'))
                continue
        elif data[off:off + len(ja_b) + 1] != ja_b + b'\0':
            rep.skipped.append((r['id'], 'ja text differs from image (stale database?)'))
            continue
        cap =(r.get('slot') or r.get('max_bytes') or 0) if r.get('fmt') == 'hwptr' else (r.get('max_bytes') or 0)
        if len(en_b) + 1 > cap:
            hint = ' (hw relocation is off: --hw-relocate on)' if r.get('fmt') == 'hwptr' and textfmt_hwkana.is_relocatable(r) else ''
            rep.failed.append((r['id'], 'does not fit in place (%d > %d bytes: fixed slot of a table, cannot be relocated)%s' % (len(en_b) + 1, cap, hint)))
            continue
        by_fmt[r['fmt']].append(r)
    new = data
    n = 0
    if hw_reloc:
        # no pointer-looking word inside any other record (record arrays, ordinary text: cp932 bytes such as 00 00 93 8c read as
        # a pointer word) may ever be rewritten
        prot = [(_hexoff(r['id']), _hexoff(r['id']) + (r.get('max_bytes') or 0)) for r in list(recs) + list(others) if r.get('fmt') != 'hwptr']
        rr, reverted, used_align = hw_relocate_fit(new, textdb.load_image(source).base, hw_reloc, getattr(res, 'refit', None), share=(share == 'dup'),
                                       force=(hw_relocate == 'force'), protect=prot, align=HW_ALIGN, guard=True, compact=HW_COMPACT)
        if reverted:
            by = {}
            for rid in reverted:
                c = res.refit.cls.get(rid) or '?'
                by[c] = by.get(c, 0) + 1
            rep.notes.append('refit forms back to the in-place short form (no 4-byte aligned room, or the record cannot be relocated): %d %s' % (
                len(reverted), ', '.join('%s %d' % kv for kv in sorted(by.items()))))
            res.refit_reverted = getattr(res, 'refit_reverted', []) + reverted
        if used_align != HW_ALIGN:
            rep.notes.append('hw strings of this overlay are placed at %d-byte alignment (no room at %d for the club words)' % (used_align, HW_ALIGN))
        new = rr.data
        rep.failed += rr.failed
        rep.skipped += rr.skipped
        st = rr.stats
        n_in = sum(1 for w, _ in rr.where.values() if w == 'in_place')
        n_mv = len(rr.where) - n_in
        rep.applied += len(rr.where)
        rep.in_place += n_in
        rep.relocated += n_mv
        if st:
            rep.notes.append('hw pool: %d strings (%d in place, %d relocated), arena %d bytes, used %d, slack %d' % (
                st['strings'], n_in, n_mv, st['capacity'], st['used'], st['slack']))
    for fmt, mod in (('hwptr', textfmt_hwkana), ('recarr', textfmt_recarray), ('gap', textfmt_gap)):
        if by_fmt[fmt]:
            new = mod.apply(new, by_fmt[fmt])
            n += len(by_fmt[fmt])
    rep.applied += n
    rep.in_place += n
    if fresh:
        res.files.append(rep)
    rep.old_size, rep.new_size = len(orig), len(new)
    if bytes(new) != orig:
        res.patches[iso] = bytes(new)
        rep.changed = True


# ------------------------------------------------------------------ driver
def build_patches(tdb='translation', append_safe=False, relocate_ptrblob=False,
                  font_dir=None, members_dir=None, files_dir=None, only=None,
                  repack=True, share='none', cross_pool=True, prop_font=False, prop_variants='A', prop_place='tail', prop_glyphs=True,
                  textures_dir=None, texture_policy='exact', money_fmt=False, money_decimal_d=True, hw_relocate='off',
                  prop_scale=False, money_style='jp', refit=False, grow_overlays=0, align_fix=False, tag_fix=False, scout_fix=False,
                  open_font=False, crowd_fix=False, bcast_speed='off', lin_center=False, small_prop=False, options_fix=False, cell_prop=False,
                  clip_lead_space=False):
    """Run stages 1-3.  Returns Result (res.patches = {iso path: bytes} of CHANGED files).
    New keywords (all default to the previous behaviour): prop_scale (fontpatch --prop-scale cave), money_style 'jp'|'western' (moneypatch.STYLES),
    refit (apply tools/refit.py overlays; implies hw_relocate 'on' unless it is 'force'), grow_overlays N (opt-in BSS-pad growth, needs append_safe),
    align_fix (fontpatch cell-count alignment: needs prop_font, variants 'A', tail placement; library default False, the command line default is on),
    tag_fix (layoutpatch short-name routine of 11 overlays; library default False, the command line default is on),
    open_font (opt-in, default False: the Roboto Condensed Medium half-width glyphs and advance table of tools/openfont.py, docs/open-font.md; needs prop_font
    with glyphs; the refit / lint width measuring of this build uses the new table too),
    crowd_fix (layoutpatch.patch_crowd: G_INCOME crowd line 'man' / 'ppl' / '0ppl'; library default False, the command line default is on),
    bcast_speed 'off'|'1.7'|'1.9'|'2.2' (layoutpatch.patch_bcast_speed: GAME.BIN commentary reveal speed; library default 'off', the command line default is 1.9),
    lin_center (fontpatch.LIN_SRC: narrow glyphs centred in the linear text writer of 1ST_READ.BIN; needs prop_font with glyphs and the tail placement;
    library default False, the command line default is on),
    small_prop (fontpatch.SMALL_SRC: the 16 px windows of OPTION.BIN and TRAINING.BIN get the proportional advance scaled by 2/3; needs prop_font with glyphs,
    variants 'A' and the tail placement; library AND command line default False, docs/layout-issues.md s17),
    options_fix (layoutpatch.patch_options: highlight windows of the in-match OPTIONS panel; library default False, the command line default is on, s18),
    cell_prop (fontpatch.CELL_SRC + layoutpatch.patch_cell_prop: the commentary subtitle line engine of GAME.BIN advances glyphs by the proportional table and drops a blank
    at the start of a wrapped line; needs prop_font with glyphs and the tail placement; library default False, the command line default is on, s19),
    clip_lead_space (build_patch.bcast_clip_text: the blank between two consecutive commentary clips is written IN FRONT of the clip that starts with a letter / digit instead of
    after every clip; needs cell_prop, because only that engine skips a blank at the first column of a line; library default False, the command line default follows --cell-prop)."""
    if clip_lead_space and not cell_prop:
        raise PipelineError("--clip-lead-space on needs --cell-prop on (the stock line engine draws a blank at the first column of a line as 12 px of indent; with --cell-prop off the trailing blank rule is used)")
    if cell_prop and not (prop_font and prop_glyphs):
        raise PipelineError("--cell-prop on needs --proportional-font on (the routine reads the proportional font's advance table; with 'control' or off there is none)")
    if cell_prop and prop_place != 'tail':
        raise PipelineError("--cell-prop on needs --prop-font-place tail (the cave reads the table of the tail placement)")
    if small_prop and not (prop_font and prop_glyphs):
        raise PipelineError("--small-prop on needs --proportional-font on (the routine reads the proportional font's advance table; with 'control' or off there is none)")
    if small_prop and (prop_place != 'tail' or prop_variants != 'A'):
        raise PipelineError("--small-prop on needs --prop-font-place tail and --prop-font-variants A")
    if bcast_speed not in ('off', '1.7', '1.9', '2.2'):
        raise PipelineError('unknown --bcast-speed %r (one of off, 1.7, 1.9, 2.2)' % (bcast_speed,))
    if money_style not in STYLES:
        raise PipelineError("unknown money style %r (one of %s)" % (money_style, ", ".join(STYLES)))
    if prop_scale and not prop_font:
        raise PipelineError("--prop-scale on needs --proportional-font on")
    if prop_scale and prop_place != 'tail':
        raise PipelineError("--prop-scale on needs --prop-font-place tail (the gap1 reserve is 128 bytes)")
    if open_font and not (prop_font and prop_glyphs):
        raise PipelineError("--open-font on needs --proportional-font on (the glyphs are drawn left aligned for the proportional advance table; with 'control' or off there is no table)")
    if lin_center and not (prop_font and prop_glyphs):
        raise PipelineError("--lin-center on needs --proportional-font on (the cave reads the proportional font's advance table; with 'control' or off there is none)")
    if lin_center and prop_place != 'tail':
        raise PipelineError("--lin-center on needs --prop-font-place tail (the cave reads the table of the tail placement)")
    if align_fix and not (prop_font and prop_glyphs):
        raise PipelineError("--align-fix on needs --proportional-font on (the fix lives in the proportional font's cave; with 'control' the glyphs stay unshifted)")
    if align_fix and prop_variants != 'A':
        raise PipelineError("--align-fix on needs --prop-font-variants A (the cave uses the registers of variant A)")
    if align_fix and prop_place != 'tail':
        raise PipelineError("--align-fix on needs --prop-font-place tail (the gap1 reserve has no room for the align cave)")
    if grow_overlays and not append_safe:
        raise PipelineError("--grow-overlays needs --append-safe (it extends that fallback to overlays with a BSS area)")
    if not 0 <= grow_overlays <= GROW_MAX:
        raise PipelineError("--grow-overlays must be between 0 and %d" % GROW_MAX)
    import pixelwidth
    open_data = None
    if open_font:
        import openfont
        try:
            open_data = openfont.load()
        except openfont.OpenFontError as e:
            raise PipelineError('open font: %s' % e)
    pixelwidth.set_open_font(open_font)      # refit / lint measure with the table of the glyph set that is built (restored below)
    try:
        return _build_patches(tdb, append_safe, relocate_ptrblob, font_dir, members_dir, files_dir, only, repack, share, cross_pool, prop_font,
                              prop_variants, prop_place, prop_glyphs, textures_dir, texture_policy, money_fmt, money_decimal_d, hw_relocate,
                              prop_scale, money_style, refit, grow_overlays, align_fix, tag_fix, scout_fix, open_data, crowd_fix, bcast_speed, lin_center,
                              small_prop, options_fix, cell_prop, clip_lead_space)
    finally:
        pixelwidth.set_open_font(False)


def _build_patches(tdb, append_safe, relocate_ptrblob, font_dir, members_dir, files_dir, only, repack, share, cross_pool, prop_font,
                   prop_variants, prop_place, prop_glyphs, textures_dir, texture_policy, money_fmt, money_decimal_d, hw_relocate,
                   prop_scale, money_style, refit, grow_overlays, align_fix, tag_fix, scout_fix, open_data, crowd_fix=False, bcast_speed='off', lin_center=False,
                   small_prop=False, options_fix=False, cell_prop=False, clip_lead_space=False):
    res = Result()
    by_src = load_tdb(tdb)
    if refit:
        if hw_relocate == 'off':
            hw_relocate = 'on'
            res.notes.append("refit: --hw-relocate forced on")
        res.refit = apply_refit(by_src, tdb, res, True)
    survey = load_survey()
    known = disc_paths()
    res.total_records = sum(len(v) for v in by_src.values())
    res.total_with_en = sum(1 for v in by_src.values() for r in v if r.get('en'))
    done_bp = False
    for source in sorted(by_src):
        recs = by_src[source]
        if only and not any(o in source for o in only):
            continue
        # skip sources with nothing to apply: output is the original file anyway
        if not any(r.get('en') for r in recs):
            continue
        h = handler_for(source)
        if h is None:
            res.unknown_sources[source] = sum(1 for r in recs if r.get('en'))
            continue
        if h == 'overlay':
            # fmt=hwptr / recarr records (tools/textfmt_hwkana.py, textfmt_recarray.py) are written in place after the
            # pool repacking, which never sees them (docs/uncovered-text.md)
            core = [r for r in recs if r.get('fmt') not in textdb.EXTRA_FMTS]
            extra = [r for r in recs if r.get('fmt') in textdb.EXTRA_FMTS]
            if any(r.get('en') for r in core) or not any(r.get('en') for r in extra):
                do_overlay(res, source, core, survey, append_safe, repack, share, cross_pool, grow_overlays)
            if any(r.get('en') for r in extra):
                do_extra(res, source, extra, hw_relocate, share, core)
        elif h == 'ptrblob':
            do_ptrblob(res, source, recs, relocate_ptrblob)
        elif h == 'ini':
            do_ini(res, source, recs)
        elif h == 'bcast':
            do_bcast(res, source, recs, clip_lead_space)
        elif h == 'bpinfo' and not done_bp:
            do_bpinfo(res, by_src)
            done_bp = True
    apply_font(res, _abs(font_dir or os.path.join('translation', 'font')))
    apply_members(res, _abs(members_dir or os.path.join('translation', 'members')))
    apply_textures(res, _abs(textures_dir or os.path.join('translation', 'textures')), texture_policy)
    apply_files(res, _abs(files_dir or os.path.join('translation', 'files')))
    apply_layout_patches(res)
    if tag_fix:
        apply_tag_fix(res)
    if scout_fix:
        apply_scout_fix(res)
    if crowd_fix:
        apply_crowd_fix(res)
    apply_bcast_speed(res, bcast_speed)
    if options_fix:
        apply_options_fix(res)
    if money_fmt:
        apply_money_fmt(res, money_decimal_d, money_style)
    if prop_font:
        apply_prop_font(res, _abs(font_dir or os.path.join('translation', 'font')), prop_variants, prop_place, prop_glyphs, prop_scale,
                        align_fix, open_data, lin_center, small_prop, cell_prop)
    for iso in res.patches:
        if iso.upper() not in known:
            raise PipelineError('%s is not a file on the disc' % iso)
    return res


def patches_digest(patches, sparse=None):
    """SHA-1 over the whole-file patches (and, only when there are any, the sparse sector edits: unchanged digest without them)."""
    h = hashlib.sha1()
    for k in sorted(patches):
        h.update(k.encode() + b'\0' + hashlib.sha1(patches[k]).digest())
    for k in sorted(sparse or {}):
        h.update(b'sparse\0' + k.encode() + b'\0')
        for off in sorted(sparse[k]):
            h.update(b'%d\0' % off + hashlib.sha1(sparse[k][off]).digest())
    return h.hexdigest()


def print_summary(res, out=None, max_fail=10):
    out = out or sys.stdout
    t = res.totals()
    w = lambda s='': print(s, file=out)
    w('=== patch summary ===')
    w('translation DB: %d records, %d with English (%d untranslated records keep the Japanese original)' % (
        t['records'], t['with_en'], t['untranslated']))
    w('applied %d strings (%d in place, %d relocated inside the image, %d appended), failed %d, skipped %d' % (
        t['applied'], t['in_place'], t['relocated'], t['appended'], t['failed'], t['skipped']))
    w('files changed: %d (%d of them font/container/code-patch/whole-file replacements), net file-size growth %+d bytes' % (
        t['files_changed'], t['asset_files'], t['growth']))
    for f in res.files:
        if not f.changed and not f.failed and not f.skipped:
            continue
        w('  %-9s %-28s %s %d -> %d (%+d)  applied=%d in_place=%d relocated=%d appended=%d failed=%d skipped=%d' % (
            f.kind, f.iso, 'CHANGED' if f.changed else 'same   ', f.old_size, f.new_size, f.new_size - f.old_size,
            f.applied, f.in_place, f.relocated, f.appended, len(f.failed), len(f.skipped)))
        for n in f.notes:
            w('      note: ' + n)
        for x in f.failed[:max_fail]:
            w('      FAILED  %s: %s' % x)
        for x in f.skipped[:max_fail]:
            w('      SKIPPED %s: %s' % x)
    for n in res.notes:
        w('  ' + n)
    for s, n in sorted(res.unknown_sources.items()):
        w('  WARNING: %d translated records for unknown source %s were ignored' % (n, s))
    if res.disc:
        d = res.disc
        w('disc: %d sectors rewritten, %d file(s) moved, end LBA %d -> %d (%+d sectors, %+d bytes)' % (
            d['sectors_rewritten'], len(d['moves']), d['orig_end_lba'], d['new_end_lba'],
            d['new_end_lba'] - d['orig_end_lba'], (d['new_end_lba'] - d['orig_end_lba']) * 2352))
        for m in d['moves']:
            w('  moved %s LBA %d -> %d (%d bytes)' % m)
        for iso, lba, size in d.get('added', ()):
            w('  added %s at LBA %d (%d bytes)' % (iso, lba, size))
        if d.get('dedupe'):
            w('  dedupe: %d identical-file group(s), %d extent(s) shared' % (len(d['dedupe']), sum(len(g[1]) for g in d['dedupe'])))
        w('  free sectors left: %d (%d bytes) below LBA %d' % (d.get('free_sectors', 0), d.get('free_sectors', 0) * 2048, d.get('max_lba', 549150)))
        for m in d.get('warnings', ()):
            w('  WARNING: %s' % m)
        w('  cue: %s' % d['cue'])
        w('  gdi: %s' % d['gdi'])
        if d.get('verify') is not None:
            w(d['verify'].text())


def flags_line(a):
    """The effective standard-build flags, printed at the end of every run (the release flags are
    --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --strict)."""
    return 'flags: --repack %s --share %s%s --proportional-font %s --refit %s --align-fix %s --tag-fix %s --scout-fix %s --crowd-fix %s --bcast-speed %s --lin-center %s%s --money-format %s --prop-scale %s%s%s --texture-policy %s' % (
        a.repack, a.share, ' --append-safe' if a.append_safe else '', a.proportional_font, a.refit, a.align_fix, a.tag_fix, a.scout_fix, a.crowd_fix, a.bcast_speed,
        a.lin_center, ' --cell-prop %s' % a.cell_prop if getattr(a, 'cell_prop', None) else '', a.money_format, a.prop_scale, ' --hw-relocate ' + a.hw_relocate if a.hw_relocate != 'off' else '',
        ' --strict' if a.strict else '', a.texture_policy) + (' --open-font on' if getattr(a, 'open_font', 'off') == 'on' else '') + (
        ' --small-prop on' if getattr(a, 'small_prop', 'off') == 'on' else '') + (
        ' --options-fix %s' % a.options_fix if hasattr(a, 'options_fix') else '') + (
        ' --clip-lead-space %s' % a.clip_lead_space if getattr(a, 'clip_lead_space', None) else '')


def check_flag_combos(a):
    """Clear errors for flag combinations the engine refuses (returns the message or None)."""
    if getattr(a, 'open_font', 'off') == 'on' and a.proportional_font != 'on':
        return '--open-font on needs --proportional-font on (the Roboto Condensed glyphs are drawn for the proportional advance table; pass --open-font off)'
    if getattr(a, 'small_prop', 'off') == 'on':
        if a.proportional_font != 'on':
            return '--small-prop on needs --proportional-font on (the routine reads the proportional advance table; pass --small-prop off)'
        if a.prop_font_place == 'gap1' or a.prop_font_variants != 'A':
            return '--small-prop on needs --prop-font-place tail and --prop-font-variants A (pass --small-prop off)'
    if a.lin_center == 'on':
        if a.proportional_font != 'on':
            return '--lin-center on needs --proportional-font on (the cave reads the proportional advance table; pass --lin-center off)'
        if a.prop_font_place == 'gap1':
            return '--lin-center on needs --prop-font-place tail (pass --lin-center off)'
    if getattr(a, 'cell_prop', 'off') == 'on':
        if a.proportional_font != 'on':
            return '--cell-prop on needs --proportional-font on (the routine reads the proportional advance table; pass --cell-prop off)'
        if a.prop_font_place == 'gap1':
            return '--cell-prop on needs --prop-font-place tail (the gap1 reserve has no room for the cell cave; pass --cell-prop off)'
    if getattr(a, 'clip_lead_space', 'off') == 'on' and getattr(a, 'cell_prop', 'off') != 'on':
        return '--clip-lead-space on needs --cell-prop on (only the --cell-prop line engine skips a blank at the first column of a line; pass --clip-lead-space off for the trailing blank rule)'
    if a.align_fix == 'on':
        if a.proportional_font != 'on':
            return '--align-fix on needs --proportional-font on (pass --align-fix off for a build without the proportional font or with --proportional-font control)'
        if a.prop_font_variants != 'A':
            return '--align-fix on needs --prop-font-variants A (pass --align-fix off to hook the B / C copies as well)'
        if a.prop_font_place == 'gap1':
            return '--align-fix on needs --prop-font-place tail (the gap1 reserve has no room for the align cave; pass --align-fix off)'
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tdb', default='translation')
    ap.add_argument('--out', default=os.path.join('build', 'out'))
    ap.add_argument('--name', default='SakaTsuku2-EN')
    ap.add_argument('--strategy', default='gap', choices=['gap', 'append'])
    ap.add_argument('--repack', choices=['on', 'off'], default='on',
                    help='overlay text: on = pool repacking (tools/textrepack.py, default), off = per-string textdb insertion')
    ap.add_argument('--share', choices=['none', 'dup'], default='none',
                    help='repack: dup = identical strings of one pool share one copy (UNPROVEN in-game: assumes strings '
                         'are read-only; big capacity gain, see docs/capacity-design.md)')
    ap.add_argument('--no-cross-pool', action='store_true', help='repack: do not move whole strings between pools')
    ap.add_argument('--append-safe', action='store_true',
                    help='OPT-IN, INFERRED (never run in-game): allow appending overflow strings after no-BSS overlays '
                         '(raises their `_end` word)')
    ap.add_argument('--relocate-ptrblob', action='store_true',
                    help='allow textfmt_ptrblob to append relocated strings to 1ST_READ.BIN/2_DP.BIN (UNSAFE/untested)')
    ap.add_argument('--proportional-font', choices=['on', 'off', 'control'], default='off',
                    help='proportional half-width font (tools/fontpatch.py, docs/proportional-font.md); UNPROVEN in-game, default off. '
                         'control = cave + hooks with an all-12 table and unshifted glyphs: must behave exactly like the original game')
    ap.add_argument('--prop-font-variants', default='A', choices=['A', 'ABC'],
                    help='which copies of the layout function to hook: A = the 98 live ones (default), ABC adds the 7 probably-dead stubs')
    ap.add_argument('--prop-font-place', default='tail', choices=['tail', 'gap1'],
                    help='where the 104-byte routine and the 256-byte table live in 1ST_READ.BIN (default: tail at 0x8c299800)')
    ap.add_argument('--money-format', choices=['on', 'money-only', 'off'], default='on',
                    help='English money text for the tsString %%m token (tools/moneypatch.py, docs/number-formats.md): the original '
                         'function prints 億/万円 pieces that no English string can replace; on = formatter in the 1ST_READ.BIN tail '
                         '(0x8c299a00) + hook in 102 overlays + %%D prints ASCII digits (default); money-only = without the %%D change; '
                         'off = original behaviour (then the translated %%m texts show Japanese amounts)')
    ap.add_argument('--money-style', choices=list(STYLES), default='jp',
                    help="money text of the %%m formatter (tools/moneypatch.py, docs/number-formats.md): jp (default) keeps the Japanese oku / man "
                         "structure in English words ('13 Oku 1500 Man', '6000 Man', '1 Oku', '0 Yen'); western = the decimal output (Y1.315bn). "
                         "Ignored with --money-format off")
    ap.add_argument('--open-font', choices=['on', 'off'], default='off',
                    help='OPT-IN, UNPROVEN in-game: the 94 ASCII half-width glyphs are Roboto Condensed Medium (SIL OFL-1.1, translation/fonts/, '
                         'tools/openfont.py, docs/open-font.md) with their own advance table (space 12 px, digits 12); needs --proportional-font on; '
                         'refit and the width lints measure with the new table; default off = output unchanged')
    ap.add_argument('--prop-scale', choices=['on', 'off'], default='off',
                    help='with --proportional-font on: windows whose advance is not 24 (16/32/48/10 px) scale the advance table by A/24 '
                         '(tools/fontpatch.py CAVE_SCALE_SRC, docs/patch-engine.md s4); default off, UNPROVEN in-game')
    ap.add_argument('--refit', choices=['on', 'off'], default='on',
                    help='apply the names owner refit overlays (tools/refit.py load_overlays) on top of the DB English before patching; '
                         'forces --hw-relocate on (unless it is force); default ON (the standard build: club words of 9+ letters print in full); '
                         'off = the slot-cut forms')
    ap.add_argument('--align-fix', choices=['on', 'off'], default=None,
                    help='with --proportional-font on: cell-count alignment of the proportional font (tools/fontpatch.py align_fix, docs/layout-issues.md s10): '
                         'blank-run columns such as the shirt numbers snap to the cell grid and the right-anchored player-card panel (CAP_SLCT / ENDOPT / EVENT) '
                         'uses pixel widths; default ON whenever the build supports it (--proportional-font on, variants A, tail placement) and OFF otherwise, so a bare `build_patch.py --dry-run` still works; an EXPLICIT --align-fix on is refused with --proportional-font off/control, --prop-font-variants other than A, --prop-font-place gap1')
    ap.add_argument('--lin-center', choices=['on', 'off'], default=None,
                    help='with --proportional-font on: the linear text writer of 1ST_READ.BIN (match intro Stadium / KICK OFF, in-match OPTIONS rows, ...) centres narrow '
                         'glyphs (i, l, I, ! ...) in their 12 px tile instead of leaving a 7 px gap behind them (tools/fontpatch.py LIN_SRC, docs/layout-issues.md s16; '
                         'works with the default proportional table and with --open-font); hook found by signature, refuses foreign / patched bytes; default ON whenever '
                         'the build has the proportional font on the tail placement and OFF otherwise; an EXPLICIT --lin-center on is refused without --proportional-font on')
    ap.add_argument('--cell-prop', choices=['on', 'off'], default=None,
                    help='with --proportional-font on: the commentary subtitle (BCAST text in the match, drawn by the line engine of FLOW_PRG/GAME.BIN, which gave every half-width '
                         'character a fixed 12 px advance: "Fi r st hal f") advances by the proportional table (cave `font.cell` in the 1ST_READ.BIN tail reading the table at '
                         '0x8c299900, clamped to 12; tools/fontpatch.py CELL_SRC, tools/layoutpatch.py patch_cell_prop, docs/layout-issues.md s19) and drops the blank that a wrap leaves '
                         'at the start of the next line; full-width glyphs, wrap logic and display loop untouched; signature located, refuses foreign / patched bytes; default ON '
                         'whenever the build has the proportional font on the tail placement and OFF otherwise; an EXPLICIT --cell-prop on is refused without --proportional-font on')
    ap.add_argument('--clip-lead-space', choices=['on', 'off'], default=None,
                    help='the blank between two consecutive commentary clips (they are drawn one behind the other, English needs a gap): ON = one LEADING blank in front of every clip '
                         'that starts with a letter / digit / opening mark (player and team names included), none before a clip that starts with , . ; : ! ? ) \' and nothing appended, so '
                         '"Grampus, ..." and "Suzuki Cuts it out" read right and a 15-letter name no longer needs a 17th byte; the blank at the first column of a line (first clip of an '
                         'utterance, line start after a wrap) is skipped by the --cell-prop engine (docs/text-sources.md s6.1, docs/layout-issues.md s19); OFF = the old rule, one TRAILING '
                         'blank after every clip except name callouts ("SuzukiCut", "Grampus ,"); default follows --cell-prop (ON with it, OFF without); an EXPLICIT --clip-lead-space on is '
                         'refused without --cell-prop on')
    ap.add_argument('--small-prop', choices=['on', 'off'], default='off',
                    help='OPT-IN, UNPROVEN in-game (default off = output unchanged): the 16 px text windows of OPTION.BIN (the option / sound-test lists) and TRAINING.BIN '
                         '(Practice player-info panel) use the proportional advance scaled by 2/3 instead of the fixed 8 px, which left a gap behind i / l / r / t '
                         '(tools/fontpatch.py SMALL_SRC, docs/layout-issues.md s17); only the advance hook of those two overlays and the unused tail of the font cave '
                         'change; needs --proportional-font on, tail placement, variants A')
    ap.add_argument('--tag-fix', choices=['on', 'off'], default='on',
                    help='short-name tag routine of 11 overlays (Practice > Player Placement, ...): the LAST name word, up to the tag width, instead of the first 4 '
                         'letters of the given name (tools/layoutpatch.py tag_patches, docs/s7t-proposals.md s2); signature located, refuses foreign bytes; default on')
    ap.add_argument('--scout-fix', choices=['on', 'off'], default='on',
                    help='scout info panel (SCDRF, SEARCH): the Age row no longer overwrites its own digits (`add #71,r4` -> `add #69,r4`, 2 halfwords per overlay; '
                         'tools/layoutpatch.py scout_patches, docs/layout-issues.md s11); signature located, refuses foreign bytes; default on')
    ap.add_argument('--crowd-fix', choices=['on', 'off'], default='on',
                    help='Event income table (FLOW_PRG/G_INCOME.BIN): the crowd line prints "1man 827ppl" / "0ppl" instead of "1ma827pp" (unit copy counts 2 -> 4 / 3, '
                         'two strings in the zero padding; tools/layoutpatch.py crowd_patches, docs/layout-issues.md s13); signature located, '
                         'refuses foreign or already patched bytes; default on')
    ap.add_argument('--options-fix', choices=['on', 'off'], default='on',
                    help='in-match OPTIONS panel (FLOW_PRG/GAME.BIN and ENDING.BIN): the selected option (ON / OFF, A / B, Near / Mid / Far) is brightened by a sprite window '
                         'of fixed character cells that fitted the Japanese full-width values; the 11 window records (data, same size) are recomputed from the cells of the '
                         'English option words (tools/layoutpatch.py options_patches, docs/layout-issues.md s18); signature located, refuses foreign or already patched bytes; default on')
    ap.add_argument('--bcast-speed', choices=['off', '1.7', '1.9', '2.2'], default='1.9',
                    help='commentary subtitle (BCAST) reveal speed in GAME.BIN (tools/layoutpatch.py bcast_patches, docs/layout-issues.md s14): off = original (2.23 ticks per '
                         'character), 1.7 = 1.67x, 1.9 = 1.94x (default), 2.2 = 2.23x (one character per tick); two sites, signature located, '
                         'refuses foreign or already patched bytes (site 2 re-dispatches behind the prologue: the first version crashed the emulator, s14); the Event / scout message typewriter is not touched')
    ap.add_argument('--grow-overlays', type=int, default=0, metavar='N',
                    help='OPT-IN, INFERRED (never booted), needs --append-safe: an overlay WITH a BSS area may take up to N appended bytes '
                         '(zero pad up to its old `_end`, strings behind it, `_end` word raised by pad + growth; per-overlay limits and the '
                         'excluded overlays: docs/pipeline.md, docs/expansion/overlay-memory.md). Default 0 = off, output unchanged')
    ap.add_argument('--hw-relocate', choices=['on', 'off', 'force'], default='off',
                    help='half-width pointer strings (club-name words, nations, leagues, foreign name parts; fmt=hwptr): on = a string '
                         'that does not fit its slot is relocated into the freed slots of the same overlay and its pointers are '
                         'rewritten (limit = per-record budget and pool slack; tools/textfmt_hwkana.apply_relocate, docs/hw-relocation.md); '
                         'off = in place only (default, UNPROVEN in-game); force = relocate every such string (test hook)')
    ap.add_argument('--font-dir')
    ap.add_argument('--members-dir')
    ap.add_argument('--files-dir')
    ap.add_argument('--textures-dir', help='default translation/textures: <iso path>/<texture id>.pvr (tools/texinject.py)')
    ap.add_argument('--textures-delta', metavar='DIR',
                    help='default off: DIR = l10n/textures (VCDIFF deltas + MANIFEST.tsv, tools/texdelta.py, docs/texture-delta.md); the repainted '
                         '.pvr files are rebuilt from them and the original textures of extracted/ into a temporary directory used as '
                         '--textures-dir (excludes --textures-dir); a texture whose original differs (other disc revision) stops the build')
    ap.add_argument('--texture-policy', choices=['exact', 'grow'], default='exact',
                    help='exact (default) = repainted textures must fit their original slot, file lengths unchanged (an over-slot texture stops the '
                         'build with ONE message naming file, id and bytes over); grow = allow containers that can be re-laid-out to grow: '
                         'INFERRED safe only, never run in-game (docs/texture-injection.md s7, docs/pipeline.md s9.1)')
    ap.add_argument('--only', nargs='*', help='only sources whose path contains one of these')
    ap.add_argument('--dry-run', action='store_true', help='do not write the disc')
    ap.add_argument('--dedupe-files', choices=['on', 'off'], default='off',
                    help='disc: on = byte-identical files (15 groups, 3726 sectors) share one extent (tools/discbuild.py, docs/disc-layout.md); '
                         'INFERRED safe (the game opens by name), never booted; default off = output unchanged')
    ap.add_argument('--allow-overflow', action='store_true',
                    help='disc: allow content past LBA 549150 (emulator-only; the default is to stop with a capacity message)')
    ap.add_argument('--add-file', action='append', default=[], metavar='/ISO/PATH=LOCAL',
                    help='disc: ship an extra file inside the image (e.g. /README.TXT=notes.txt); repeatable; default none')
    ap.add_argument('--verify-disc', choices=['off', 'fast', 'full'], default='fast',
                    help='disc: run tools/verify_disc.py on the written image (fast = structure, both ISO readers, patched files '
                         'read back, changed sectors; full = every sector and every file); a failure exits with 3')
    ap.add_argument('--club-guard', choices=['on', 'off'], default='on',
                    help='club-name composer bounded to 13 characters + NUL in the 20 overlays (tools/layoutpatch.py, docs/layout-issues.md s9); '
                         'off = original unbounded composer')
    ap.add_argument('--club-dot', choices=['on', 'off'], default='on',
                    help='a town cut by the club-name guard ends in "." (off: plain prefix)')
    ap.add_argument('--dump', help='also write every changed file below this directory')
    ap.add_argument('--strict', action='store_true', help='exit 2 if any string failed or was skipped')
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.align_fix is None:       # default: on where the engine supports it, off otherwise (explicit 'on' keeps the clear error)
        a.align_fix = 'on' if (a.proportional_font == 'on' and a.prop_font_variants == 'A' and a.prop_font_place != 'gap1') else 'off'
    if a.lin_center is None:      # default: on where the build has the proportional table (explicit 'on' keeps the clear error)
        a.lin_center = 'on' if (a.proportional_font == 'on' and a.prop_font_place != 'gap1') else 'off'
    if a.cell_prop is None:       # default: on where the build has the proportional table (explicit 'on' keeps the clear error)
        a.cell_prop = 'on' if (a.proportional_font == 'on' and a.prop_font_place != 'gap1') else 'off'
    if a.clip_lead_space is None:  # default: follows --cell-prop (the leading blank needs its blank-at-column-0 skip; explicit 'on' without it keeps the clear error)
        a.clip_lead_space = a.cell_prop
    msg = check_flag_combos(a)
    if msg:
        print('ERROR: %s' % msg, file=sys.stderr)
        return 1
    LAYOUT_OPTS['guard'] = a.club_guard == 'on'
    LAYOUT_OPTS['dot'] = a.club_dot == 'on'
    if a.textures_delta:                  # l10n/textures deltas + the player's extracted/ -> a temporary --textures-dir
        if a.textures_dir:
            print('ERROR: --textures-delta and --textures-dir exclude each other', file=sys.stderr)
            return 1
        import atexit
        import shutil
        import tempfile
        import texdelta
        os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
        tmp = tempfile.mkdtemp(prefix='l10n_texdelta_', dir=os.path.join(ROOT, 'build'))
        atexit.register(shutil.rmtree, tmp, True)
        try:
            _, problems = texdelta.apply_all(_abs(a.textures_delta), EXTRACTED, tmp)
        except (texdelta.TexDeltaError, OSError) as e:
            problems = [str(e)]
        if problems:
            for pr in problems:
                print('ERROR: textures-delta: %s' % pr, file=sys.stderr)
            return 1
        a.textures_dir = tmp
    try:
        res = build_patches(a.tdb, a.append_safe, a.relocate_ptrblob, a.font_dir, a.members_dir, a.files_dir, a.only,
                            a.repack == 'on', a.share, not a.no_cross_pool,
                            a.proportional_font != 'off', a.prop_font_variants, a.prop_font_place,
                            a.proportional_font == 'on', a.textures_dir, a.texture_policy,
                            a.money_format != 'off', a.money_format == 'on', a.hw_relocate,
                            a.prop_scale == 'on', a.money_style, a.refit == 'on', a.grow_overlays, a.align_fix == 'on', a.tag_fix == 'on', scout_fix=a.scout_fix == 'on',
                            crowd_fix=a.crowd_fix == 'on', bcast_speed=a.bcast_speed,
                            open_font=a.open_font == 'on', lin_center=a.lin_center == 'on', small_prop=a.small_prop == 'on',
                            options_fix=a.options_fix == 'on', cell_prop=a.cell_prop == 'on', clip_lead_space=a.clip_lead_space == 'on')
    except PipelineError as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 1
    if a.dump:
        for iso, data in res.patches.items():
            p = os.path.join(_abs(a.dump), *iso.strip('/').split('/'))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                f.write(data)
    if not a.dry_run:
        import discbuild
        extra = {}
        for spec in a.add_file:
            k, _, v = spec.partition('=')
            if not v:
                print('ERROR: --add-file wants /ISO/PATH=LOCAL, got %r' % spec, file=sys.stderr)
                return 1
            try:
                with open(_abs(v), 'rb') as f:
                    extra[k] = f.read()
            except OSError as e:
                print('ERROR: --add-file %s: %s' % (spec, e), file=sys.stderr)
                return 1
        try:
            res.disc = discbuild.build_disc(res.patches, _abs(a.out), a.name, ROOT, a.strategy, extra, None,
                                            a.dedupe_files == 'on', a.allow_overflow, sparse=res.sparse or None)
        except (discbuild.DiscFull, discbuild.DiscError) as e:
            print('ERROR: %s' % e, file=sys.stderr)
            return 1
        if a.verify_disc != 'off':
            import verify_disc
            expect = dict(res.patches)
            expect.update(extra)
            for iso, ed in res.sparse.items():        # whole-file SHA-1 of the sparse-patched file, streamed
                expect[iso] = discbuild.sparse_sha1(ROOT, iso, ed)
            res.disc['verify'] = verify_disc.verify_disc(
                _abs(a.out), a.name, ROOT, expect=expect, rewritten=res.disc['rewritten_lbas'],
                sectors='all' if a.verify_disc == 'full' else 'auto', read_files=a.verify_disc == 'full')
    print_summary(res)
    print(flags_line(a))
    print('patch digest %s, %.1fs' % (patches_digest(res.patches, res.sparse), time.time() - t0))
    t = res.totals()
    if a.strict and (t['failed'] or t['skipped'] or res.unknown_sources):
        print('ERROR: --strict: %d string(s) failed, %d skipped, %d unknown source(s) with English: exit 2' % (
            t['failed'], t['skipped'], len(res.unknown_sources)), file=sys.stderr)
        return 2
    if res.disc and res.disc.get('verify') is not None and not res.disc['verify'].ok:
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main())
