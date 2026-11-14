"""refit: opt-in re-fit overlays for the slot-forced rough English short forms (docs/hw-relocation.md).

Why.  Many English strings of the translation DB are abbreviations that exist ONLY because a pool slot was too small
(`Sie` for the club word Cielo in a 4-byte slot, `Rumostk`, `Ros`, `Yoko.FC`, `Arg.`, `Casab.` ...).  With half-width string
relocation (`build_patch --hw-relocate on`) and pool repacking the slot is no longer the limit, so a proper form can be
written.  The default build must keep working with 0 failed, so the better forms live in OVERLAY files and are applied on
top of the loaded DB only when asked for:

    translation/refit/<source with / replaced by __>.jsonl      one record per line:
        {"id": "FLOW_PRG/DRAFT.BIN#21f64", "ja": "ｼｴﾛ", "en": "Cielo", "why": "club word (Italian 'sky')", "cls": "club"}
    id    the id of an existing DB record (the same id as in translation/*.jsonl)
    ja    optional but always written: the Japanese text, checked against the DB (a stale overlay record is skipped)
    en    the better English (replaces the DB `en` of that record, nothing else of the record changes)
    why   short reason (class of the fit, authority)
    cls   field class for the cap check: club | jclub | nation | city | person | town | sponsor | other

API (for tools/build_patch.py, `--refit on`):

    refit.load_overlays(db_by_source, overlay_dir=None, relocate=True, report=None) -> [modified records]
        db_by_source = build_patch.load_tdb(...) ({source: [records]}).  The DB record dicts are CHANGED IN PLACE (en only)
        and returned.  relocate=False (build flag --hw-relocate off): a refit that does not fit the in-place slot of a
        pointer-referenced hwptr record is skipped, so the build keeps 0 failed with relocation off.
    refit.apply_overlays(db_by_source, ...) -> (new_db_by_source, report)    same, copy-on-write, the input is not touched
    refit.validate(db_by_source, overlay_dir=None, relocate=True, simulate=False, sources=None) -> Report
        record shape, id / ja match, cp932, hard field cap, class caps (characters, pixel width of tools/pixelwidth.py
        against the widest Japanese string of the same pointer table), and with simulate=True the REAL build code
        (build_patch.do_overlay / do_extra, share dup, append-safe, repack on) per source: no refit may fail or add a failure.

CLI:
    python -I -X utf8 tools/refit.py list                     counts per overlay file / class
    python -I -X utf8 tools/refit.py validate [--sim] [--sources FLOW_PRG/DRAFT.BIN ...] [--hw off]
Nothing is written anywhere by this module.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

REFIT_DIR = os.path.join(ROOT, 'translation', 'refit')
CLASSES = ('club', 'jclub', 'nation', 'city', 'person', 'town', 'sponsor', 'other')
# class caps: (max characters, hard) -- docs/expansion/field-widths.md 2.3 / 2.4 / 2.6
#   club    <= 9: the longest one-slot art spelling (Avalanche, Corriente); the composed `town short + word` lives in the 14-byte `#sname#` (13 chars)
#   person  <= 12: 14-byte name field, only 12 characters are shown on the player card (docs/layout-issues.md 3)
CLASS_CHARS = {'club': 9, 'jclub': 14, 'nation': 14, 'city': 14, 'person': 12, 'town': 12, 'sponsor': 24, 'other': 24}
TBL = re.compile(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]')
CELL_PX = 12

_PX = None


def _pixelwidth():
    global _PX
    if _PX is None:
        import pixelwidth
        _PX = pixelwidth
    return _PX


def _enc(s):
    """cp932 bytes of a DB string (tools/textdb.encode_text rules); ValueError / UnicodeEncodeError when not encodable"""
    import textfmt_common as C
    return C.encode_text(s)


def source_of(rid):
    return rid.rsplit('#', 1)[0]


# ------------------------------------------------------------------ reading
class Report:
    """modified: [rec]; before: {id: old en}; cls: {id: field class of the form}; skipped / problems: [(id, code, message)]; sim: {source: dict}"""

    def __init__(self):
        self.modified = []
        self.before = {}
        self.cls = {}
        self.skipped = []
        self.problems = []
        self.checked = 0
        self.sim = {}
        self.files = {}

    def ok(self):
        return not self.problems

    def summary(self):
        by = {}
        for _id, code, _m in self.skipped:
            by[code] = by.get(code, 0) + 1
        return 'refit: %d records modified, %d skipped %s, %d problems' % (len(self.modified), len(self.skipped), by, len(self.problems))


def overlay_files(overlay_dir=None):
    d = overlay_dir or REFIT_DIR
    if not os.path.isdir(d):
        return []
    return sorted(p for p in glob.glob(os.path.join(d, '*.jsonl')) if not os.path.basename(p).startswith('_'))


def read_overlay(path):
    """-> [dict]; raises ValueError with file:line on a malformed record"""
    out = []
    with open(path, encoding='utf-8') as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError as ex:
                raise ValueError('%s:%d: not JSON (%s)' % (os.path.basename(path), ln, ex))
            if not isinstance(r, dict):
                raise ValueError('%s:%d: record is not an object' % (os.path.basename(path), ln))
            for k in ('id', 'en', 'why'):
                if not isinstance(r.get(k), str) or not r[k]:
                    raise ValueError('%s:%d: field %r missing or empty' % (os.path.basename(path), ln, k))
            if '#' not in r['id']:
                raise ValueError('%s:%d: id %r has no #offset' % (os.path.basename(path), ln, r['id']))
            if 'ja' in r and not isinstance(r['ja'], str):
                raise ValueError('%s:%d: ja must be a string' % (os.path.basename(path), ln))
            if r.get('cls', 'other') not in CLASSES:
                raise ValueError('%s:%d: unknown cls %r' % (os.path.basename(path), ln, r.get('cls')))
            out.append(r)
    return out


def read_all(overlay_dir=None):
    """-> [(path, [records])]; duplicate ids across the overlay files raise ValueError"""
    seen = {}
    out = []
    for p in overlay_files(overlay_dir):
        recs = read_overlay(p)
        for r in recs:
            if r['id'] in seen:
                raise ValueError('duplicate overlay id %s in %s and %s' % (r['id'], seen[r['id']], os.path.basename(p)))
            seen[r['id']] = os.path.basename(p)
        out.append((p, recs))
    return out


def index_db(db_by_source):
    return {r['id']: r for recs in db_by_source.values() for r in recs}


# ------------------------------------------------------------------ hard caps (what the build itself enforces)
def slot_of(rec):
    return rec.get('slot') or rec.get('max_bytes') or 0


def hard_cap(rec, relocate):
    """-> bytes (incl. NUL) the English of this record may use in the build: the in-place slot, or for a relocatable
    pointer-referenced hwptr record (hw relocation on) the per-record budget."""
    if rec.get('fmt') == 'hwptr':
        import textfmt_hwkana
        if relocate and textfmt_hwkana.is_relocatable(rec):
            return max(rec.get('max_bytes') or 0, slot_of(rec))
        return slot_of(rec)
    return rec.get('max_bytes') or 0


def check_hard(rec, en, relocate):
    """-> None or (code, message) for the limits that make the build FAIL a record"""
    try:
        b = _enc(en)
    except (UnicodeEncodeError, ValueError) as ex:
        return 'encode', 'not encodable in cp932: %s' % ex
    if rec.get('fmt') == 'hwptr' and not relocate and len(b) + 1 > slot_of(rec):
        return 'needs-reloc', 'needs %d bytes, in-place slot is %d (hw relocation is off)' % (len(b) + 1, slot_of(rec))
    cap = hard_cap(rec, relocate)
    if rec.get('fmt') in ('hwptr', 'recarr') and len(b) + 1 > cap:
        return 'cap', '%d bytes exceed the field cap %d' % (len(b) + 1, cap)
    if rec.get('fmt') not in ('hwptr', 'recarr'):
        ctx = rec.get('ctx') or ''
        fixed = not rec.get('refs') or 'orphan' in ctx or 'interior' in ctx or 'stride-table' in ctx
        if fixed and len(b) + 1 > (rec.get('max_bytes') or 0):
            return 'cap', '%d bytes exceed the fixed field of %s bytes (no pointer / interior pointer / stride table: cannot move)' % (
                len(b) + 1, rec.get('max_bytes'))
    return None


# ------------------------------------------------------------------ applying
def _apply(db_by_source, overlay_dir, relocate, report, copy):
    rep = report or Report()
    idx = index_db(db_by_source)
    newdb = {s: list(v) for s, v in db_by_source.items()} if copy else db_by_source
    pos = {}
    if copy:
        for s, v in newdb.items():
            for i, r in enumerate(v):
                pos[r['id']] = (s, i)
    for path, recs in read_all(overlay_dir):
        rep.files[os.path.basename(path)] = len(recs)
        for ov in recs:
            rec = idx.get(ov['id'])
            if rec is None:
                rep.skipped.append((ov['id'], 'unknown-id', 'no such record in the DB'))
                continue
            if 'ja' in ov and ov['ja'] != rec.get('ja'):
                rep.skipped.append((ov['id'], 'stale', 'ja differs from the DB (%r vs %r)' % (ov['ja'], rec.get('ja'))))
                continue
            if not rec.get('en'):
                rep.skipped.append((ov['id'], 'untranslated', 'the DB record has no English; a refit only improves a translation'))
                continue
            if rec['en'] == ov['en']:
                continue
            bad = check_hard(rec, ov['en'], relocate)
            if bad:
                rep.skipped.append((ov['id'], bad[0], bad[1]))
                continue
            rep.before[ov['id']] = rec['en']
            rep.cls[ov['id']] = ov.get('cls')
            if copy:
                s, i = pos[ov['id']]
                new = dict(rec)
                new['en'] = ov['en']
                newdb[s][i] = new
            else:
                new = rec
                rec['en'] = ov['en']
            rep.modified.append(new)
    return newdb, rep


def load_overlays(db_by_source, overlay_dir=None, relocate=True, report=None):
    """Apply the overlays on top of the loaded DB IN PLACE (en of the matching records only) -> [modified records]."""
    _db, rep = _apply(db_by_source, overlay_dir, relocate, report, False)
    return rep.modified


def apply_overlays(db_by_source, overlay_dir=None, relocate=True, report=None):
    """Copy-on-write variant: -> (new {source: [records]}, Report); the input DB and its records are not modified."""
    return _apply(db_by_source, overlay_dir, relocate, report, True)


# ------------------------------------------------------------------ class caps
def table_of(rec):
    m = TBL.search(rec.get('ctx') or '')
    return (source_of(rec['id']), m.group(1)) if m else None


_WIDTHS = {'db': None, 'w': {}}


def family_cap_px(db_by_source, rec):
    """pixel budget of the field family: the widest ORIGINAL Japanese string (cells * 12 px) of the same pointer table, or of
    the record itself / its slot (12 * (slot - 1)) when it has no table.  The layout of the original game had to show that
    width, so no refit may be wider than it.  The table widths of the last DB are cached (strong reference, so no id reuse)."""
    key = table_of(rec)
    own = max(len(_enc(rec['ja'])), slot_of(rec) - 1 if rec.get('fmt') in ('hwptr', 'recarr') else 0)
    if key is None:
        return CELL_PX * own
    if _WIDTHS['db'] is not db_by_source:
        _WIDTHS['db'] = db_by_source
        _WIDTHS['w'] = {}
    w = _WIDTHS['w']
    if key not in w:
        m = 0
        for r in db_by_source.get(key[0], ()):
            if table_of(r) == key:
                m = max(m, len(_enc(r['ja'])))
        w[key] = m
    return CELL_PX * max(w[key], own)


def check_class(db_by_source, rec, en, cls):
    """-> list of (code, message) for the class caps: characters and pixel width"""
    out = []
    n = len(en)
    cap = CLASS_CHARS.get(cls, 24)
    if n > cap:
        out.append(('chars', '%d characters exceed the %s cap of %d' % (n, cls, cap)))
    px = _pixelwidth()
    end, _last = px.line_px(en)
    if cls in ('person',):
        lim = CELL_PX * CLASS_CHARS['person'] + 13
    else:
        lim = family_cap_px(db_by_source, rec) + CELL_PX      # one cell of tolerance: the Japanese strings live on the 12 px cell grid
    if end > lim:
        out.append(('px', '%d px wide, the widest Japanese string of its table is %d px (+1 cell allowed)' % (end, lim - CELL_PX)))
    return out


# ------------------------------------------------------------------ validation
def _sim_source(build_patch, source, recs, relocate, detail=False, report=None):
    """real build code on one source, in memory -> (set of failed ids, set of skipped ids); detail=True: ({id: reason}, {id: reason})"""
    BP = build_patch
    if BP.handler_for(source) != 'overlay':      # BPINFO (one fixed 14-byte field per name), INI ...: nothing to place
        return ({}, {}) if detail else (set(), set())
    core = [r for r in recs if r.get('fmt') not in BP.textdb.EXTRA_FMTS]
    extra = [r for r in recs if r.get('fmt') in BP.textdb.EXTRA_FMTS]
    res = BP.Result()
    res.refit = report         # the build's fallback (forms given back when an overlay has no aligned room) needs before / cls
    survey = BP.load_survey()
    if any(r.get('en') for r in core) or not any(r.get('en') for r in extra):
        BP.do_overlay(res, source, core, survey, True, True, 'dup', True)
    if any(r.get('en') for r in extra):
        BP.do_extra(res, source, extra, 'on' if relocate else 'off', 'dup', core)
    if detail:
        return ({fid: w for f in res.files for fid, w in f.failed}, {fid: w for f in res.files for fid, w in f.skipped})
    failed = {fid for f in res.files for fid, _w in f.failed}
    skipped = {fid for f in res.files for fid, _w in f.skipped}
    return failed, skipped


def simulate_db(db_by_source, sources, relocate=True, report=None):
    """-> {source: (failed ids, skipped ids)} of the real build code with the DB as given (in memory, nothing written)"""
    import build_patch
    return {s: _sim_source(build_patch, s, db_by_source[s], relocate, False, report) for s in sources if s in db_by_source}


def validate(db_by_source, overlay_dir=None, relocate=True, simulate=False, sources=None):
    """Check every overlay record (see the module docstring).  simulate=True runs the real build on each touched
    source with and without the overlay.  -> Report (ok() when there is no problem)."""
    rep = Report()
    idx = index_db(db_by_source)
    touched = set()
    for path, recs in read_all(overlay_dir):
        rep.files[os.path.basename(path)] = len(recs)
        for ov in recs:
            rep.checked += 1
            rid = ov['id']
            rec = idx.get(rid)
            if rec is None:
                rep.problems.append((rid, 'unknown-id', 'no such record in the DB'))
                continue
            src = source_of(rid)
            if sources and src not in sources:
                continue
            if 'ja' in ov and ov['ja'] != rec.get('ja'):
                rep.problems.append((rid, 'stale', 'ja differs from the DB'))
                continue
            if not rec.get('en'):
                rep.problems.append((rid, 'untranslated', 'DB record has no English'))
                continue
            bad = check_hard(rec, ov['en'], relocate)
            if bad and bad[0] == 'needs-reloc':           # hw relocation off: the loader skips it, not a problem
                rep.skipped.append((rid,) + bad)
                continue
            if bad:
                rep.problems.append((rid,) + bad)
                continue
            for code, msg in check_class(db_by_source, rec, ov['en'], ov.get('cls', 'other')):
                rep.problems.append((rid, code, msg))
            touched.add(src)
    if simulate and touched:
        base = simulate_db(db_by_source, sorted(touched), relocate)
        new_db, _r = apply_overlays(db_by_source, overlay_dir, relocate)
        after = simulate_db(new_db, sorted(touched), relocate)
        for s in sorted(touched):
            bf, bs = base[s]
            af, as_ = after[s]
            rep.sim[s] = {'base_failed': len(bf), 'after_failed': len(af), 'new_failed': sorted(af - bf), 'new_skipped': sorted(as_ - bs)}
            for fid in sorted(af - bf):
                rep.problems.append((fid, 'sim-failed', 'fails in the real build with the refit overlay'))
            for fid in sorted(as_ - bs):
                rep.problems.append((fid, 'sim-skipped', 'skipped in the real build with the refit overlay'))
    return rep


# ------------------------------------------------------------------ CLI
def _load_db():
    import build_patch
    return build_patch.load_tdb('translation')


def main(argv):
    if not argv or argv[0] not in ('list', 'validate'):
        print(__doc__)
        return 2
    cmd = argv[0]
    reloc = True
    if '--hw' in argv:
        reloc = argv[argv.index('--hw') + 1] != 'off'
    od = None
    if '--dir' in argv:
        od = argv[argv.index('--dir') + 1]
    if cmd == 'list':
        tot = 0
        by = {}
        for path, recs in read_all(od):
            tot += len(recs)
            for r in recs:
                by[r.get('cls', 'other')] = by.get(r.get('cls', 'other'), 0) + 1
            print('%-48s %6d' % (os.path.basename(path), len(recs)))
        print('total %d records, by class %s' % (tot, by))
        return 0
    srcs = None
    if '--sources' in argv:
        i = argv.index('--sources') + 1
        srcs = set()
        while i < len(argv) and not argv[i].startswith('--'):
            srcs.add(argv[i])
            i += 1
    db = _load_db()
    rep = validate(db, od, relocate=reloc, simulate="--sim" in argv, sources=srcs)
    print('checked %d overlay records in %d files' % (rep.checked, len(rep.files)))
    for fid, code, msg in rep.problems[:60]:
        print('PROBLEM', code, fid, msg)
    for s, d in sorted(rep.sim.items()):
        print('sim', s, d['base_failed'], '->', d['after_failed'])
    print('OK' if rep.ok() else '%d problems' % len(rep.problems))
    return 0 if rep.ok() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
