"""rfit_gen: generate the refit overlays translation/refit/<source>.jsonl (names owner tool; see tools/refit.py).

    python -I -X utf8 tools/re/rfit_gen.py [--out DIR] [--dry-run] [--no-names] [--max-sim N]

Sources of a better form, in priority order
  A  translation/refit/forms.tsv      curated club words / J.League names / nations / cities / cups / places / persons
  R  record arrays and fixed pools    the same authority, written IN PLACE (no relocation needed) when it fits the field
  B  the name pool                    (1) the longer English of the same `ja` in the BPINFO name tables (authoritative: the
                                      player's own record), (2) hepburn(ja) for Japanese surnames in the Japanese region of
                                      the sorted pool when the current English is a squeezed / kunrei spelling of it
Every candidate is checked with tools/refit.py (cp932, field cap, class caps, pixel width of the table) and the relocatable
hwptr candidates are accepted as far as the REAL build code (build_patch.do_overlay / do_extra, share dup, append-safe, repack
on, hw relocation on) still places every string of every source: all (ja, new English) units are applied, the sources that
gain a failure lose their lowest-priority units (everywhere: a form is used in every overlay or in none), repeated until the
real build shows no new failure (select_units).
Plain text records (fmt none, e.g. `Yoko.FC`) are accepted per source when the pool repacking still places everything.
Writes: translation/refit/<source with / -> __>.jsonl and translation/refit/_report.txt (ignored by the loader).
Nothing else is touched; the main DB files are only read.
"""
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import refit as RF  # noqa: E402
import rfit_kana as K  # noqa: E402
import build_patch as BP  # noqa: E402

TBL = RF.TBL
SELT = re.compile(r'^(n<=|n>=|n=|fmt=)(.*)$')
FOREIGN_KANA = set('ｰｨｪｧｩｫ')
# readings whose Hepburn form is a different word ('Hamada' + ani = elder brother), never refit by rule
EXCLUDE_JA = {'ﾊﾏﾀﾞｱﾆ'}
VOW = re.compile(r'[aeiouy]', re.I)
CONS4 = re.compile(r'[bcdfghjklmnpqrstvwxz]{4,}', re.I)


# ------------------------------------------------------------------ helpers
def tinfo(rec):
    m = TBL.search(rec.get('ctx') or '')
    return (int(m.group(1), 16), int(m.group(2)), int(m.group(3))) if m else None


def kind_of(rec):
    ctx = rec.get('ctx') or ''
    fmt = rec.get('fmt') or 'ptr'
    if 'hwpool' in ctx:
        return 'hwpool'
    if 'orphan' in ctx or (fmt == 'ptr' and not rec.get('refs')):
        return 'orphan'
    if 'interior' in ctx:
        return 'interior'
    if fmt == 'recarr':
        return 'recarr'
    if fmt == 'hwptr':
        return 'hwptr'
    return 'ptr'


def parse_forms(path):
    out = []
    with open(path, encoding='utf-8') as fh:
        for ln, line in enumerate(fh, 1):
            if not line.strip() or line.startswith('#'):
                continue
            p = line.rstrip('\n').split('\t')
            if len(p) < 5:
                raise ValueError('%s:%d: need 5 tab separated columns' % (os.path.basename(path), ln))
            cls, ja, en, sel, why = p[:5]
            if cls not in RF.CLASSES:
                raise ValueError('%s:%d: unknown class %r' % (os.path.basename(path), ln, cls))
            out.append({'cls': cls, 'ja': ja, 'alts': [x.strip() for x in en.split(' | ')], 'sel': sel.split(), 'why': why, 'order': len(out)})
    return out


def _one(s, t, fmt):
    if s == '*':
        return True
    if s == 'notbl':
        return not t
    m = SELT.match(s)
    if not m:
        raise ValueError('bad selector %r' % s)
    op, val = m.groups()
    if op == 'fmt=':
        return fmt == val
    if not t:
        return False
    n = t[2]
    if op == 'n<=':
        return n <= int(val)
    if op == 'n>=':
        return n >= int(val)
    return n in [int(x) for x in val.split(',')]


def sel_ok(sel, rec):
    """space separated conditions are ANDed, `a|b` inside one condition is an OR"""
    t = tinfo(rec)
    fmt = rec.get('fmt') or 'ptr'
    return all(any(_one(alt, t, fmt) for alt in s.split('|')) for s in sel)


def junk(en):
    return bool(CONS4.search(en) or (len(en) > 1 and not VOW.search(en)) or en.endswith('.'))


def is_subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


def bp_canon(by_src):
    """{key: en}: the English of the BPINFO name records (13 / 14-byte fields) keyed by ja and by ja without blanks;
    only when one form has >= 70 percent of the votes"""
    votes = defaultdict(Counter)
    for src, recs in by_src.items():
        if not src.endswith('BPINFO.BIN'):
            continue
        for r in recs:
            if r.get('en'):
                votes[r['ja']][r['en']] += 1
                votes[r['ja'].replace(' ', '')][r['en']] += 1
    out = {}
    for k, c in votes.items():
        top, n = c.most_common(1)[0]
        if n >= 0.7 * sum(c.values()):
            out[k] = top
    return out


def japanese_region(recs):
    """ids of the hwptr name-pool records after the last coarse restart (foreign names a..n, then Japanese surnames a..n)"""
    seq = []
    for r in recs:
        t = tinfo(r)
        if r.get('fmt') == 'hwptr' and t and t[2] >= 60:
            seq.append((t[0], t[1], r))
    seq.sort(key=lambda x: (x[0], x[1]))
    last = None
    prev = None
    for k, (_a, _i, r) in enumerate(seq):
        b = r['ja'].encode('cp932', 'replace')[0]
        if prev is not None and prev >= 0xD0 and b <= 0xB8:
            last = k
        prev = b
    if last is None:
        return set()
    return {r['id'] for _a, _i, r in seq[last:]}


# ------------------------------------------------------------------ candidates
class Cand:
    __slots__ = ('rec', 'new', 'cls', 'why', 'tier', 'pri', 'unit', 'source', 'kind', 'free')

    def __init__(self, rec, new, cls, why, tier, pri):
        self.rec, self.new, self.cls, self.why, self.tier, self.pri = rec, new, cls, why, tier, pri
        self.source = RF.source_of(rec['id'])
        self.kind = kind_of(rec)
        self.unit = (rec['ja'], new)
        self.free = False


def static_ok(by_src, rec, en, cls):
    """-> None or reason string (hard field cap with relocation on, class caps)"""
    bad = RF.check_hard(rec, en, True)
    if bad:
        return '%s: %s' % bad
    for code, msg in RF.check_class(by_src, rec, en, cls):
        return '%s: %s' % (code, msg)
    return None


def gen_candidates(by_src, forms, names):
    cands = []
    unfit = []                       # (rec, wanted, reason)
    taken = set()
    for f in forms:
        hit = 0
        for src in sorted(by_src):
            for rec in by_src[src]:
                if rec['ja'] != f['ja'] or not rec.get('en') or not sel_ok(f['sel'], rec):
                    continue
                hit += 1
                if rec['id'] in taken:
                    continue
                chosen, why_not = None, None
                for alt in f['alts']:
                    if alt == rec['en']:
                        chosen, why_not = alt, 'same'
                        break
                    r = static_ok(by_src, rec, alt, f['cls'])
                    if r is None:
                        chosen = alt
                        break
                    why_not = r
                if why_not == 'same':
                    continue
                if chosen is None:
                    unfit.append((rec, f['alts'][0], why_not))
                    continue
                taken.add(rec['id'])
                c = Cand(rec, chosen, f['cls'], '%s (was %r)' % (f['why'], rec['en']), 'A', (0, f['order']))
                cands.append(c)
        if not hit:
            print('note: form for %r matched no record' % f['ja'])
    if names:
        canon = bp_canon(by_src)
        for src in sorted(by_src):
            recs = by_src[src]
            jr = japanese_region(recs)
            for rec in recs:
                if not rec.get('en') or rec['id'] in taken or rec.get('fmt') not in ('hwptr', 'recarr'):
                    continue
                if '\n' in rec['ja'] or src.endswith('BPINFO.BIN'):
                    continue
                ja, old = rec['ja'], rec['en']
                new, why = None, None
                c = canon.get(ja) or canon.get(ja.replace(' ', ''))
                if c and c != old and len(c) > len(old):
                    new, why = c, 'name from the BPINFO player record'
                elif rec.get('fmt') == 'hwptr' and rec['id'] in jr and ja not in EXCLUDE_JA and not (set(ja) & FOREIGN_KANA) and 'ｳﾞ' not in ja:
                    hep = K.hepburn(ja)
                    if hep and len(hep) > len(old) and len(hep) <= 12 and hep != old:
                        e = old.lower().replace('.', '').replace(' ', '')
                        h = hep.lower().replace(' ', '')
                        kun = re.sub(r'(?<!s)si', 'shi', e)
                        kun = re.sub(r'(?<!c)ti', 'chi', kun)
                        kun = kun.replace('tu', 'tsu').replace('hu', 'fu').replace('zi', 'ji')
                        if h == kun or is_subseq(e, h):
                            new, why = hep, 'Hepburn reading of a Japanese surname'
                if not new:
                    continue
                r = static_ok(by_src, rec, new, 'person')
                if r:
                    unfit.append((rec, new, r))
                    continue
                bad = 3 * junk(old) + (len(new) - len(old)) + (4 if old.endswith('.') else 0)
                cands.append(Cand(rec, new, 'person', '%s (was %r)' % (why, old), 'B', (1, -bad, ja)))
    # free = fits the in-place slot of the record (no relocation, no pool): record arrays, hwpool, and hwptr that fit
    for c in cands:
        rec = c.rec
        b = len(RF._enc(c.new)) + 1
        c.free = rec.get('fmt') == 'recarr' or (rec.get('fmt') == 'hwptr' and b <= RF.slot_of(rec)) or \
            c.kind in ('hwpool',)
    return cands, unfit


# ------------------------------------------------------------------ simulation helpers
def apply_cands(by_src, cands):
    new = {s: list(v) for s, v in by_src.items()}
    pos = {}
    for s, v in new.items():
        for i, r in enumerate(v):
            pos[r['id']] = (s, i)
    for c in cands:
        s, i = pos[c.rec['id']]
        r = dict(c.rec)
        r['en'] = c.new
        new[s][i] = r
    return new


_BASE = {}


_REASON = {}                 # id -> failure text of the last simulations


def sim(by_src, sources):
    """{source: failed ids} of the real build code (in memory); the failure texts are kept in _REASON"""
    out = {}
    for s in sorted(sources):
        f, _sk = RF._sim_source(BP, s, by_src[s], True, detail=True)
        out[s] = set(f)
        _REASON.update(f)
    return out



def base_failed(by_src, sources):
    miss = [s for s in sources if s not in _BASE]
    if miss:
        _BASE.update(sim(by_src, miss))
    return {s: _BASE[s] for s in sources}


def ok_with(by_src, cands, max_new=0):
    """True when the candidates add no failure in any source they touch"""
    srcs = sorted({c.source for c in cands})
    if not srcs:
        return True
    db = apply_cands(by_src, cands)
    base = base_failed(by_src, srcs)
    after = sim(db, srcs)
    for s in srcs:
        if after[s] - base[s]:
            return False
    return True


def select_units(by_src, units, log, unfit, max_iter=12):
    """Keep as many (ja, new English) units as the REAL build can place, lowest priority dropped first.

    units = [(unit, [Cand])] in priority order.  Loop: apply every remaining candidate, run the real build code on every
    touched source.  A source F that gains a failure
      * for a STRUCTURAL failure (the slot cannot move: another pointer target lies inside it, padding not free, refs
        mismatch) loses only that record (it stays as it is in that overlay; listed in `unfit`),
      * for `no room in the pool` the sources F lose their lowest-priority units (a unit is dropped in EVERY overlay: a
        form is used everywhere or nowhere); the number k of units dropped is found by bisection, simulating only F
    and the loop repeats until no source gains a failure: the last full pass had no new failure, so the result is verified
    by construction."""
    sel = [[u, list(cs)] for u, cs in units]
    for it in range(max_iter):
        flat = [c for _u, cs in sel for c in cs]
        srcs = sorted({c.source for c in flat})
        base = base_failed(by_src, srcs)
        t0 = time.time()
        after = sim(apply_cands(by_src, flat), srcs)
        bad = {s: after[s] - base[s] for s in srcs if after[s] - base[s]}
        log('  pass %d: %d units, %d records, %d sources, %d with new failures (%.0fs)' % (
            it + 1, len([1 for _u, cs in sel if cs]), len(flat), len(srcs), len(bad), time.time() - t0))
        if not bad:
            return [(u, cs) for u, cs in sel if cs]
        owner = {c.rec['id']: i for i, (_u, cs) in enumerate(sel) for c in cs}
        drop_recs = {i for ids in bad.values() for i in ids if 'no room in the pool' not in _REASON.get(i, '')}
        cap_srcs = {s for s, ids in bad.items() if any('no room in the pool' in _REASON.get(i, '') for i in ids)}
        for rid in sorted(drop_recs):
            i = owner.get(rid)
            if i is None:
                continue
            for c in sel[i][1]:
                if c.rec['id'] == rid:
                    unfit.append((c.rec, c.new, _REASON.get(rid, 'cannot be relocated')[:100]))
            sel[i][1] = [c for c in sel[i][1] if c.rec['id'] != rid]
        if cap_srcs:
            touching = [i for i, (_u, cs) in enumerate(sel) if any(c.source in cap_srcs for c in cs)]     # priority order
            fbase = base_failed(by_src, sorted(cap_srcs))

            def passes(k):
                keep = touching[:len(touching) - k] if k < len(touching) else []
                kept = {i for i in keep}
                cs = [c for i, (_u, cl) in enumerate(sel) for c in cl
                      if c.source in cap_srcs and (i in kept or i not in touching_set)]
                aft = sim(apply_cands(by_src, cs), sorted(cap_srcs))
                return all(not (aft[s] - fbase[s]) for s in cap_srcs)
            touching_set = set(touching)
            lo, hi = 0, len(touching)                    # smallest k (units dropped) that passes
            while lo < hi:
                mid = (lo + hi) // 2
                t1 = time.time()
                ok = passes(mid)
                log('    drop the %d lowest-priority of %d units touching %d sources: %s (%.0fs)' % (
                    mid, len(touching), len(cap_srcs), 'ok' if ok else 'still failing', time.time() - t1))
                if ok:
                    hi = mid
                else:
                    lo = mid + 1
            for i in touching[len(touching) - lo:]:
                for c in sel[i][1]:
                    unfit.append((c.rec, c.new, 'no room in the pool of its overlay (real build, lowest priority first)'))
                sel[i][1] = []
    raise RuntimeError('select_units: no fixed point after %d passes' % max_iter)


# ------------------------------------------------------------------ main
def main(argv):
    out_dir = os.path.join(ROOT, 'translation', 'refit')
    if '--out' in argv:
        out_dir = argv[argv.index('--out') + 1]
    dry = '--dry-run' in argv
    names = '--no-names' not in argv
    t0 = time.time()

    def log(s):
        print(s, flush=True)

    by_src = BP.load_tdb('translation')
    orig = by_src
    forms = parse_forms(os.path.join(ROOT, 'translation', 'refit', 'forms.tsv'))
    cands, unfit = gen_candidates(by_src, forms, names)
    log('candidates: %d (A %d, B %d), free %d, static-unfit %d' % (
        len(cands), sum(c.tier == 'A' for c in cands), sum(c.tier == 'B' for c in cands), sum(c.free for c in cands), len(unfit)))
    if '--cands' in argv:
        cnt = Counter((c.tier, c.cls, c.kind, c.free) for c in cands)
        for k, v in sorted(cnt.items()):
            log('  %s' % ((k, v),))
        for rec, new, why in unfit[:40]:
            log('  unfit %s %r -> %r: %s' % (rec['id'], rec['en'], new, why[:100]))
        return 0
    if '--all' in argv:                      # diagnostics: every candidate, no selection (not a valid overlay set)
        chosen, rest = list(cands), []
    else:
        chosen = [c for c in cands if c.free]
        rest = [c for c in cands if not c.free]
    if chosen and rest:
        # the free forms (fit their slot in place, record arrays) are part of the pools that the others are tested against
        by_src = apply_cands(by_src, chosen)
        _BASE.clear()
    # units: same (ja, new English) in every overlay; ptr (non hw) records are decided per source below
    hw_units = defaultdict(list)
    ptr_cands = []
    for c in rest:
        if c.rec.get('fmt') == 'hwptr':
            hw_units[c.unit].append(c)
        else:
            ptr_cands.append(c)
    def unit_key(item):
        u, cs = item
        return min(c.pri for c in cs)
    units = sorted(hw_units.items(), key=unit_key)
    if units:
        log('%d hw units (%d records); selecting against the real build' % (len(units), sum(len(cs) for _u, cs in units)))
        sel = select_units(by_src, units, log, unfit)
        took = [c for _u, cs in sel for c in cs]
        log('%d of %d hw units placed (%d records)' % (len(sel), len(units), len(took)))
        chosen += took
        by_src = apply_cands(by_src, took)         # the plain text candidates below see the hw forms; chosen keeps the originals
        _BASE.clear()
    # plain text records: per source
    by_srcp = defaultdict(list)
    for c in ptr_cands:
        by_srcp[c.source].append(c)
    for s in sorted(by_srcp):
        acc = []
        for c in sorted(by_srcp[s], key=lambda c: c.pri):
            if ok_with(by_src, acc + [c]):
                acc.append(c)
            else:
                unfit.append((c.rec, c.new, 'pool full: the repacking of %s cannot place it without a failure' % s))
        chosen += acc
    log('chosen %d records, unfit %d (%.0fs)' % (len(chosen), len(unfit), time.time() - t0))
    # rough forms that cannot be touched at all: a longer English of the same ja exists, the record cannot move
    cids = {c.rec['id'] for c in chosen}
    known = {r['id'] for r, _n, _w in unfit}
    longest = {}
    for recs in orig.values():
        for r in recs:
            en = r.get('en')
            if en and '\n' not in en and not r['id'].split('#')[0].endswith('BPINFO.BIN'):
                if len(en) > len(longest.get(r['ja'], '')):
                    longest[r['ja']] = en
    fixed = Counter()
    for recs in orig.values():
        for r in recs:
            en = r.get('en')
            if not en or r['id'] in cids or r['id'] in known:
                continue
            k = kind_of(r)
            L = longest.get(r['ja'])
            if k in ('interior', 'orphan', 'hwpool') and L and len(L) > len(en) and (en.endswith('.') or L[:3].lower() == en[:3].lower()) \
                    and not L.endswith(('-gun', '-cho', '-mura', ' Pref.')):
                fixed[k] += 1
                why = {'interior': 'another pointer targets the middle of the string: it cannot move, slot %s bytes' % r.get('max_bytes'),
                       'orphan': 'no pointer: addressed by index / computed offset (stride table), slot %s bytes' % r.get('max_bytes'),
                       'hwpool': 'hw pool addressed by index: in place only, slot %s bytes' % (r.get('slot') or r.get('max_bytes'))}[k]
                unfit.append((r, L, why))
    # ---------------------------------------------------------------- write
    per = defaultdict(list)
    for c in chosen:
        per[c.source].append(c)
    stats = Counter()
    if not dry:
        os.makedirs(out_dir, exist_ok=True)
        for p in RF.overlay_files(out_dir):
            os.remove(p)
        for s in sorted(per):
            lst = sorted(per[s], key=lambda c: int(c.rec['id'].rsplit('#', 1)[1], 16))
            p = os.path.join(out_dir, s.replace('/', '__') + '.jsonl')
            with open(p + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
                for c in lst:
                    fh.write(json.dumps({'id': c.rec['id'], 'ja': c.rec['ja'], 'en': c.new, 'why': c.why, 'cls': c.cls}, ensure_ascii=False) + '\n')
            os.replace(p + '.tmp', p)
    for c in chosen:
        stats[(c.tier, c.cls, c.kind)] += 1
    rep = []
    rep.append('refit overlays: %d records in %d files' % (len(chosen), len(per)))
    for k, v in sorted(stats.items()):
        rep.append('  %-3s %-8s %-9s %6d' % (k[0], k[1], k[2], v))
    bykind = Counter()
    byreason = Counter()
    for rec, new, why in unfit:
        bykind[kind_of(rec)] += 1
        byreason[why.split(':')[0][:60]] += 1
    rep.append('not refit (candidates that could not be placed): %d' % len(unfit))
    for k, v in sorted(bykind.items()):
        rep.append('  by kind %-9s %6d' % (k, v))
    for k, v in sorted(byreason.items(), key=lambda kv: -kv[1])[:12]:
        rep.append('  by reason %-60s %6d' % (k, v))
    rep.append('')
    rep.append("unfit records (one line per distinct ja / new form / reason; names that only lacked pool room are counted above, not listed):")
    seen = set()
    for rec, new, why in unfit:
        if 'no room in the pool' in why and rec.get('fmt') == 'hwptr' and (tinfo(rec) or (0, 0, 0))[2] >= 60:
            continue
        key = (rec["ja"], new, why[:40])
        if key in seen or len(seen) >= 1500:
            continue
        seen.add(key)
        rep.append("  %s	%s	%r -> %r	%s" % (rec["id"], rec["ja"], rec["en"], new, why[:140]))
    text = '\n'.join(rep)
    print(text[:3000])
    if not dry:
        with open(os.path.join(out_dir, '_report.txt'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text + '\n')
        if '--no-verify' not in argv and '--all' not in argv:
            # final proof: the written overlays through the public API, real build code, hw relocation on and off
            for reloc in (True, False):
                v = RF.validate(orig, out_dir, relocate=reloc, simulate=True)
                log('verify (hw relocation %s): %d records checked, %d problems' % ('on' if reloc else 'off', v.checked, len(v.problems)))
                for p in v.problems[:20]:
                    log('  PROBLEM %s' % (p,))
                if not reloc:
                    log('  (hw relocation off: %d records skipped by the loader because they need relocation)' % len(v.skipped))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
