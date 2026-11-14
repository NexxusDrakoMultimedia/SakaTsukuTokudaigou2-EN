"""textfmt_hwkana: pointer-referenced HALF-WIDTH KATAKANA strings of the SH-4 overlays (club-name pool, national teams,
league / cup names, foreign player names, sponsor and company names ...).

Why this exists (docs/uncovered-text.md): tools/textdb.py accepts only strings with at least one full-width
character ("hw-only strings are not extracted, known gap" - docs/overlay-text.md s2).  The game keeps many name pools
as C string literals in half-width katakana (cp932 0xA1-0xDF, e.g. ｻﾘｰﾚ, ﾐｭｰﾄｽ, ﾏｲﾁｰﾑ, ﾌﾞﾗｼﾞﾙ) which a pointer table
references.  They reach the screen as club names ('Another club was founded at the same time ... "ｻﾘｰﾚ"',
'Aogashi + ﾐｭｰﾄｽ'), national-team names, league names and company names.  They were never extracted.

A string = NUL-terminated run at a pointer target (an aligned word == base + offset) that
  * is NUL-preceded (or at offset 0) and consists only of half-width katakana (0xA1-0xDF), blanks, '.', '-' and a few
    upper-case letters, with >= 2 half-width kana and no character repeated three times;
  * is not inside / overlapping a region that tools/textdb.py already extracted ('exclude');
  * is not code: the SH-4 opcode stream also contains 0xA1-0xDF bytes, so a candidate must be a member of a pointer
    table (a neighbouring word at +-4 also points at an accepted string / another hw candidate) OR have >= 4 kana.
A second pass ("pool", refs 0) adds strings NOTHING points at that sit in a run of >= 6 strings which abut each other
(only zero padding between them; textdb strings count as links of the run): half-width pools addressed by index or
computed offset (the 8-byte club-name slots of NENREP.BIN, competition names such as 'J1ﾌｧｰｽﾄｽﾃｰｼﾞ', industry names
'#to#ﾌﾟﾛﾊﾟﾝ').  Pool candidates may mix half-width kana with a little ASCII / game markup / common full-width kanji.
Slot width (`max_bytes`) = string + NUL + the zero padding behind it, never over a pointed offset and never more
than up to the next non-zero byte (the pools are 4-aligned: usually 4, 8, 12 ...).  In place only: the English
must be <= slot-1 bytes (slot = rec['slot'] if present, else max_bytes).  Pointer-referenced records (refs > 0, not
'hwpool') can instead be RELOCATED: apply_relocate() packs the English strings into the freed slots of the same overlay
and redirects every pointer word (docs/hw-relocation.md).  `max_bytes` of such a record is then the per-record budget and
the original slot is kept in `slot` (tools/re/hwr_raise_budget.py).

Record: {"id": "<source>#<hexoff>", "ja": "ﾐｭｰﾄｽ", "en": "", "max_bytes": 8, "refs": N,
         "ctx": "hwptr tbl@<first word>[i/n] stride-table(in-place only)" | "hwpool run=N stride-table(in-place only)",
         "fmt": "hwptr"}
(the words 'stride-table(in-place only)' mark the record as fixed for tools/translib.is_fixed / transwork.)
API: extract(data, base, source, exclude=None) -> records ; apply(data, entries) -> bytes (in place)
     apply_relocate(data, base, entries, share=False, force=False, align=1) -> Relocation (in place + relocation)
CLI: python -I -X utf8 tools/textfmt_hwkana.py SOURCE..   (e.g. FLOW_PRG/BACKUP.BIN; prints the strings found)
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textfmt_common as C  # noqa: E402
import hwguard as G  # noqa: E402

ROOT = os.path.dirname(HERE)

HWCH = rb'(?:[\xa1-\xdf])'
HWRUN = re.compile(rb'([\xa1-\xdf][\xa1-\xdf A-Z.\-]*)\x00')
HWRUN_ANY = re.compile(rb'(?<=\x00)([\xa1-\xdf][\xa1-\xdf A-Z.\-]{2,23})\x00')
REP3 = re.compile(rb'(.)\1\1')
MIN_KANA = 2
SOLO_KANA = 4          # a string that is not in a pointer table needs this many kana


def _kana_count(b):
    return sum(1 for c in b if 0xA1 <= c <= 0xDF)


def _bad_dakuten(b):
    """a voiced mark (0xDE / 0xDF) must follow a kana, not start the string or follow another mark / blank"""
    for i, c in enumerate(b):
        if c in (0xDE, 0xDF):
            if i == 0 or not (0xA6 <= b[i - 1] <= 0xDD):
                return True
    return False


POOL_RUN = 6            # an unreferenced hw string is accepted inside a run of this many abutting hw strings


POOLSTR = re.compile(rb'(?<=\x00)((?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e]|[\xa1-\xdf]){3,40})\x00')


MARKUP = re.compile(r'#[a-z0-9]+#|%[-0-9.]*[sdDmfxX]|@[A-Z]/|@|=[A-Za-z]/')


def _pool_ok(b):
    """text quality of a hw / mixed pool string: decodable, common kanji only, little ASCII besides game markup,
    full-width part not larger than twice the half-width part (the noise in code / tables fails at least one)"""
    try:
        s = b.decode('cp932')
    except Exception:
        return False
    import textfmt_recarray as R
    t = MARKUP.sub('', s)
    asc = sum(1 for ch in t if ord(ch) < 0x80 and ch not in ' .-')
    full = sum(1 for ch in t if ord(ch) > 0x7f and not 0xff61 <= ord(ch) <= 0xff9f)
    hw = sum(1 for ch in t if 0xff61 <= ord(ch) <= 0xff9f)
    if asc > 3 or full > 2 * hw:
        return False
    if any('\u4e00' <= ch <= '\u9fff' for ch in t) and R._level1_ratio(t) < 1.0:
        return False
    return True


def cand_all(data):
    """every NUL-preceded, 4-aligned cp932 string with >= 3 half-width kana (pure hw words, or hw mixed with ASCII /
    full-width characters such as 'J1ﾌｧｰｽﾄｽﾃｰｼﾞ' or 'ｽﾎﾟｰﾂﾆｭｰｽ ６'): {offset: bytes}"""
    out = {}
    for m in POOLSTR.finditer(data):
        o = m.start(1)
        b = m.group(1)
        if o % 4 or _kana_count(b) < 3 or REP3.search(b) or _bad_dakuten(b) or len(set(b)) < 3:
            continue
        if not _pool_ok(b):
            continue
        out[o] = b
    return out


def _pool_records(data, source, have, cands, excluded, pointed, bridge):
    """Strings nothing points at (a pool addressed by index / computed offset, e.g. the 8-byte club-name slots of
    NENREP.BIN) that sit in a run of >= POOL_RUN hw strings which abut each other (only zero padding in between)."""
    import bisect
    offs = sorted(cands)
    nxt = {}
    for o in offs:
        j = o + len(cands[o]) + 1
        while j < len(data) and data[j] == 0:
            j += 1
        nxt[o] = j if (j in cands or j in bridge) else None
    for a0, e0 in bridge.items():
        nxt[a0] = e0 if (e0 in cands or e0 in bridge) else None
    out = []
    prev_of = {v: k for k, v in nxt.items() if v is not None}
    heads = sorted(o for o in set(offs) | set(bridge) if o not in prev_of)
    for o in heads:
        run = [o]
        while nxt.get(run[-1]) is not None:
            run.append(nxt[run[-1]])
        if len(run) < POOL_RUN:
            continue
        for t in run:
            if t not in cands:
                continue                  # a bridge node (already a textdb record)
            rid = '%s#%x' % (source, t)
            b = cands[t]
            if rid in have or excluded(t, t + len(b) + 1):
                continue
            j = t + len(b) + 1
            while j < len(data) and data[j] == 0:
                j += 1
            k = bisect.bisect_right(pointed, t + len(b))
            if k < len(pointed):
                j = min(j, pointed[k])
            out.append({'id': rid, 'ja': C.decode_text(b), 'en': '', 'max_bytes': j - t, 'refs': 0,
                        'ctx': 'hwpool run=%d stride-table(in-place only)' % len(run), 'fmt': 'hwptr'})
    return out


def extract(data, base, source, exclude=None):
    import bisect
    n = len(data) // 4
    words = struct.unpack('<%dI' % n, data[:n * 4])
    lo, hi = base, base + len(data)
    targets = {}
    for i, w in enumerate(words):
        if lo <= w < hi:
            targets.setdefault(w - base, []).append(i * 4)
    ex = sorted(exclude or [])
    starts = [a for a, _ in ex]

    def excluded(a, b):
        i = max(bisect.bisect_right(starts, a) - 1, 0)
        while i < len(ex) and ex[i][0] < b:
            if ex[i][1] > a:
                return True
            i += 1
        return False

    cand = {}
    for t in sorted(targets):
        if t == 0 or data[t - 1] != 0 or t >= len(data) - 2:
            continue
        m = HWRUN.match(data, t)
        if not m:
            continue
        b = m.group(1)
        if _kana_count(b) < MIN_KANA or REP3.search(b) or _bad_dakuten(b):
            continue
        cand[t] = b
    pointed = sorted(targets)
    wordtgt = {}
    for t in cand:
        for w in targets[t]:
            wordtgt[w] = t
    # words that point at any accepted textdb string also count as table evidence
    recs = []
    for t, b in sorted(cand.items()):
        if excluded(t, t + len(b) + 1):
            continue
        in_table = False
        for w in targets[t]:
            for nb in (w - 4, w + 4):
                if nb in wordtgt or (0 <= nb // 4 < n and lo <= words[nb // 4] < hi and
                                     excluded(words[nb // 4] - base, words[nb // 4] - base + 1)):
                    in_table = True
        if not in_table and _kana_count(b) < SOLO_KANA:
            continue
        # slot: string + NUL + zero padding, not over a pointed offset
        e = t + len(b)
        j = e + 1
        k = bisect.bisect_right(pointed, e)
        limit = pointed[k] if k < len(pointed) else len(data)
        while j < len(data) and j < limit and data[j] == 0:
            j += 1
        w0 = targets[t][0]
        recs.append({'id': '%s#%x' % (source, t), 'ja': C.decode_text(b), 'en': '', 'max_bytes': j - t,
                     'refs': len(targets[t]), 'ctx': 'hwptr ptr@%x' % w0, 'fmt': 'hwptr'})
    # pointer-table context like textdb's 'tbl@<first word>[i/n]' (consecutive words that point at hw strings)
    word = [int(r['ctx'].split('@')[1], 16) for r in recs]
    i = 0
    while i < len(recs):
        j = i
        while j + 1 < len(recs) and word[j + 1] == word[j] + 4:
            j += 1
        for k in range(i, j + 1):
            if j > i:
                recs[k]['ctx'] = 'hwptr tbl@%x[%d/%d] stride-table(in-place only)' % (word[i], k - i, j - i + 1)
            else:
                recs[k]['ctx'] = 'hwptr ptr@%x stride-table(in-place only)' % word[i]
        i = j + 1
    bridge = {a0: e0 for a0, e0 in ex}
    recs += _pool_records(data, source, {r['id'] for r in recs}, cand_all(data), excluded, pointed, bridge)
    recs.sort(key=lambda r: int(r['id'].rsplit('#', 1)[1], 16))
    return recs


def slot_of(rec):
    """the true in-place slot of a record: `slot` when the budget tool raised max_bytes, else max_bytes"""
    return rec.get('slot') or rec['max_bytes']


def is_relocatable(rec):
    """pointer-referenced record (some pointer word names it; a pool addressed by index / computed offset is not) that is not on the
    denylist translation/hw_inplace.tsv (tools/hwguard.py: the pointer is the base of a table, or its use is unknown)"""
    return (rec.get('fmt') == 'hwptr' and (rec.get('refs') or 0) > 0 and 'hwpool' not in (rec.get('ctx') or '')
            and not G.is_denied(rec['id']))


def fixed_reason(rec):
    """why a hwptr record can only be written in place (text for messages)"""
    d = G.load_deny().get(rec['id'])
    if d:
        return 'relocation denied (%s: %s)' % (d[0], d[1])
    if 'hwpool' in (rec.get('ctx') or ''):
        return 'addressed by index (hwpool)'
    return 'not pointer-referenced'


def apply(data, entries):
    buf = bytearray(data)
    for e in entries:
        en = e.get('en')
        if not en:
            continue
        off = int(e['id'].rsplit('#', 1)[1], 16)
        w = slot_of(e)
        b = C.encode_text(en)
        if len(b) > w - 1:
            raise ValueError('%s: %r is %d bytes, slot holds %d' % (e['id'], en, len(b), w - 1))
        ja = C.encode_text(e['ja'])
        if bytes(buf[off:off + len(ja) + 1]) != ja + b'\x00':
            raise ValueError('%s: string no longer holds the Japanese text' % e['id'])
        buf[off:off + w] = b + b'\x00' * (w - len(b))
    return bytes(buf)


# ------------------------------------------------------------------ relocation
class Relocation:
    """Result of apply_relocate().  data: new image bytes; where: {id: ('in_place' | 'relocated', offset)};
    failed / skipped: [(id, reason)]; stats: capacity / used / slack bytes of the pool arena and counts."""

    def __init__(self, data):
        self.data = data
        self.where = {}
        self.failed = []
        self.skipped = []
        self.stats = {}


def _words(data, base):
    n = len(data) // 4
    words = struct.unpack('<%dI' % n, data[:n * 4])
    lo, hi = base, base + len(data)
    targets = {}
    for i, w in enumerate(words):
        if lo <= w < hi:
            targets.setdefault(w - base, []).append(i * 4)
    return targets


class _Item:
    __slots__ = ('rec', 'off', 'slot', 'ja_b', 'en_b', 'reloc', 'words', 'movable', 'need', 'mv', 'frozen')

    def __init__(self, rec, off, slot, ja_b, en_b):
        self.rec, self.off, self.slot, self.ja_b, self.en_b = rec, off, slot, ja_b, en_b
        self.reloc = self.movable = self.need = self.mv = self.frozen = False
        self.words = []


def _merge(iv):
    iv = sorted(x for x in iv if x[1] > x[0])
    out = []
    for a, b in iv:
        if out and out[-1][1] >= a:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _place(keep, moving, share, align):
    """One placement pass.  keep: items written in place; moving: items to relocate.  Free space = the tails of the kept
    items' slots + the whole slots of the moving ones (the Japanese in them is dead once the English is written).
    Best fit, longest string first.  Returns (placements {item: new offset}, unplaced items, largest free run)."""
    import bisect
    free = _merge([(i.off + len(i.en_b) + 1, i.off + i.slot) for i in keep if not i.frozen] + [(i.off, i.off + i.slot) for i in moving])
    runs = []                       # sorted (usable size, aligned start, end): bisect finds the best fit (smallest run that holds the string)

    def add(a, b):
        s = (a + align - 1) // align * align
        if b > s:
            bisect.insort(runs, (b - s, s, b))
    for a, b in free:
        add(a, b)
    groups = {}
    for it in sorted(moving, key=lambda i: i.off):
        groups.setdefault(it.en_b if share else (it.en_b, it.off), []).append(it)
    order = sorted(groups.values(), key=lambda g: (-len(g[0].en_b), g[0].off))
    placed, unplaced = {}, []
    for g in order:
        need = len(g[0].en_b) + 1
        k = bisect.bisect_left(runs, (need,))
        if k == len(runs):
            unplaced += g
            continue
        _size, s, b = runs.pop(k)
        add(s + need, b)
        for it in g:
            placed[it] = s
    return placed, unplaced, max([r[0] for r in runs] or [0])


def apply_relocate(data, base, entries, share=False, force=False, align=1, protect=(), guard=False, compact=True, index=None):
    """In-place writing plus RELOCATION of pointer-referenced half-width strings.

    A translated record whose English fits its slot (`slot`, else `max_bytes`) is written in place exactly like apply()
    (the result is byte-identical to apply() when nothing needs to move).  A pointer-referenced record whose English does
    not fit is relocated: the pool arena is the slots of all translated pointer-referenced records of this image (tails
    of the in-place ones, whole slots of the moving ones); best-fit-decreasing packs the moving strings into it, then every
    pointer word that held base+old is rewritten to base+new.  `max_bytes` is the per-record budget of a relocatable
    record (it may exceed the slot).  A string that finds no room FAILS and keeps its Japanese bytes (its slot leaves the
    arena and the pass is repeated until stable); no byte outside the slots of translated records is ever written.
    share: identical English strings of the image share one copy; force: relocate every string (test hook: round trip of
    the whole pool); align: start alignment of relocated strings in bytes; protect: [(start, end)] byte ranges of other
    records (record arrays) in which a pointer-looking word must never be rewritten.
    A record with another pointer target inside its slot (a suffix pointer) is only ever written in place, as apply()
    does, and its slot is not lent to other strings.
    A record that is not relocatable (denylist translation/hw_inplace.tsv, hwpool, no pointer) is only ever written in place and its
    slot is never lent either: it can be the head of a table or a field of a record.  guard=True (build_patch) additionally checks
    the pointer sites of every relocatable record in the image with tools/hwguard.py and treats everything that is not shown to
    be a text pointer (literal used with an index, lone data field, ...) like a denied record: fail safe, it stays where it is.
    index: a prepared hwguard.ImageIndex(data, base) for guard=True.
    compact=False tries only the plan that moves the strings that do not fit (least movement; the default also tries the repacking of all).
    Bad records never raise: they land in .failed / .skipped."""
    import bisect
    if guard:
        G.require_deny()            # fail safe: no denylist file = no guarded build
    compact_ok = compact
    res = Relocation(data)
    targets = _words(data, base)
    tgt_sorted = sorted(targets)
    ix = index                  # hwguard.ImageIndex of `data` (a caller that places repeatedly passes one)
    items = []
    for e in entries:
        if not e.get('en'):
            continue
        off = int(e['id'].rsplit('#', 1)[1], 16)
        try:
            ja_b = C.encode_text(e['ja'])
            en_b = C.encode_text(e['en'])
        except (UnicodeEncodeError, ValueError) as ex:
            res.skipped.append((e['id'], 'unencodable: %s' % ex))
            continue
        if bytes(data[off:off + len(ja_b) + 1]) != ja_b + b'\0':
            res.skipped.append((e['id'], 'ja text differs from image (stale database?)'))
            continue
        slot = slot_of(e)
        rel = is_relocatable(e)
        why_fixed = '' if rel else fixed_reason(e)
        if rel and guard:
            if ix is None:
                ix = G.ImageIndex(data, base)
            cls, why = G.site_verdict(ix.site_report(off))
            if cls != 'text':
                rel, why_fixed = False, 'relocation refused (%s: %s)' % (cls, why)
        top = max(e['max_bytes'], slot) if rel else slot
        if len(en_b) + 1 > top:
            res.failed.append((e['id'], 'does not fit in place (%d > %d bytes)%s' % (
                len(en_b) + 1, top, '' if rel else ' and cannot be relocated: ' + why_fixed)))
            continue
        if off + slot > len(data) or any(data[off + len(ja_b) + 1:off + slot]):
            res.failed.append((e['id'], 'slot padding is not free (stale slot width %d)' % slot))
            continue
        k = bisect.bisect_right(tgt_sorted, off)
        inner = tgt_sorted[k] - off if k < len(tgt_sorted) and tgt_sorted[k] < off + slot else 0
        it = _Item(e, off, slot, ja_b, en_b)
        it.frozen = bool(inner) or not rel          # a record that cannot move never lends its tail: it may be a field of a record
        need = len(en_b) + 1 > slot or (force and rel)
        if need and inner:
            res.failed.append((e['id'], 'cannot be relocated: another pointer target (+%d) lies inside the slot of %d bytes' % (inner, slot)))
            continue
        if need and not rel:
            res.failed.append((e['id'], 'does not fit in place (%d > %d bytes) and cannot be relocated: %s' % (
                len(en_b) + 1, slot, why_fixed)))
            continue
        if rel:
            words = targets.get(off, [])
            if len(words) == e['refs']:
                it.words, it.movable = words, not inner
            elif need:
                res.failed.append((e['id'], 'cannot be relocated: %d pointer word(s) found, record says %s' % (len(words), e['refs'])))
                continue
        it.need = need
        items.append(it)
    # the slots must be disjoint: a stale or doubled record must never let two strings share bytes
    items.sort(key=lambda i: i.off)
    clean, end = [], -1
    for it in items:
        if it.off < end:
            res.failed.append((it.rec['id'], 'slot overlaps the slot of another record'))
            continue
        clean.append(it)
        end = it.off + it.slot
    items = clean
    # a pointer word that lies inside a slot we rewrite would be destroyed
    starts = [i.off for i in items]
    prot = sorted(protect)
    pstarts = [a for a, _ in prot]
    for it in list(items):
        for w in it.words:
            k = bisect.bisect_right(starts, w) - 1
            j = bisect.bisect_right(pstarts, w) - 1
            if (k >= 0 and items[k].off <= w < items[k].off + items[k].slot) or (j >= 0 and prot[j][0] <= w < prot[j][1]):
                if it.need:
                    res.failed.append((it.rec['id'], 'a pointer word lies inside a slot or record that is being rewritten / protected'))
                    items.remove(it)
                else:
                    it.movable, it.words = False, []
                break
    # Two plans: (min) only the strings that do not fit move; (compact) every movable string is repacked, which also
    # reclaims the tails of the small slots.  Keep the plan with fewer failures (min on a tie: least movement).
    plans = []
    for compact in ((False, True) if compact_ok else (False,)):
        if compact and not any(i.need for i in items):
            continue
        its = list(items)
        failed = []
        while True:
            for i in its:
                i.mv = i.need or (compact and i.movable)
            placed, unplaced, largest = _place([i for i in its if not i.mv], [i for i in its if i.mv], share, align)
            if not unplaced:
                break
            drop = set()
            for i in unplaced:
                if i.need:
                    failed.append((i.rec['id'], 'no room in the pool (needs %d bytes, largest free run %d: the slack of this image is used up)' % (
                        len(i.en_b) + 1, largest)))
                    drop.add(id(i))
                else:
                    i.movable = False       # stays where it is
            its = [i for i in its if id(i) not in drop]
        plans.append((len(failed), compact, its, placed, failed, {id(i): i.mv for i in its}))
    plans.sort(key=lambda x: (x[0], x[1]))
    _, _, items, placed, failed, mvs = plans[0]
    res.failed += failed
    for i in items:
        i.reloc = mvs[id(i)]
    buf = bytearray(data)
    for it in items:
        buf[it.off:it.off + it.slot] = b'\0' * it.slot
    for it in items:
        if not it.reloc:
            buf[it.off:it.off + len(it.en_b)] = it.en_b
            res.where[it.rec['id']] = ('in_place', it.off)
    uniq = {}
    for it, s in placed.items():
        buf[s:s + len(it.en_b)] = it.en_b
        for w in it.words:
            struct.pack_into('<I', buf, w, base + s)
        res.where[it.rec['id']] = ('relocated', s)
        uniq[s] = len(it.en_b) + 1
    # read-back proof: every pointer of every relocated record resolves to its English
    for it, s in placed.items():
        for w in it.words:
            t = struct.unpack_from('<I', buf, w)[0] - base
            if bytes(buf[t:t + len(it.en_b) + 1]) != it.en_b + b'\0':
                raise RuntimeError('%s: relocation read-back failed' % it.rec['id'])
    cap = sum(i.slot for i in items)
    used = sum(len(i.en_b) + 1 for i in items if not i.reloc) + sum(uniq.values())
    res.stats = {'strings': len(items), 'in_place': len(items) - len(placed), 'relocated': len(placed),
                 'capacity': cap, 'used': used, 'slack': cap - used}
    res.data = bytes(buf)
    return res


def main(argv):
    sys.path.insert(0, HERE)
    import textdb as T
    for src in argv:
        img = T.load_image(src)
        strs, ptrs, _ = T.extract_image(img)
        ex = [(s.off, s.off + s.max_bytes) for s in strs]
        recs = extract(img.data, img.base, src, ex)
        print('%s: %d hw strings, slot bytes %d' % (src, len(recs), sum(r['max_bytes'] for r in recs)))
        for r in recs[:int(os.environ.get('N', '12'))]:
            print('   %-8s %-24s slot %-3d refs %d %s' % (r['id'].split('#')[1], r['ja'], r['max_bytes'], r['refs'], r['ctx']))


if __name__ == '__main__':
    main(sys.argv[1:])
