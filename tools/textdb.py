"""textdb: text extractor / reinserter for the SH-4 overlay images.

Sources handled (paths relative to extracted/):
    FLOW_PRG/*.BIN   flat SH-4 memory images (tools/overlay.py)
    ATFIRST/*.BIN    only those that tools/overlay.py accepts as overlays
                     (FACEMDUL.BIN, HELP.BIN, TITLE.BIN)
    1ST_READ.BIN is scanned too (load address 0x8C010000) but see docs/overlay-text.md.

A string is a NUL-terminated cp932 byte run that
  * is the target of at least one aligned 32-bit absolute pointer (load_addr + offset)
    stored in the image  ("referenced"), or
  * is an unreferenced "orphan" candidate (strict plausibility rules, in-place only).
Every string must pass a plausibility test (see classify_text) and contain at least
one double-byte (full-width) character.

JSONL database (one file per source, translation/<dir>__<file>.jsonl):
    {"id": "FLOW_PRG/X.BIN#3f204", "ja": "...", "en": "", "max_bytes": N, "refs": N|null, "ctx": "..."}
plus "orphan": true for unreferenced strings.  "ja" holds real characters for cp932 text,
"\\n" for 0x0a and <XX> tokens (upper-case hex) for every byte that is not plain ASCII
printable or part of a cp932 double byte / half-width katakana char that round-trips;
a literal '<' is written <3C>.

CLI:
    python -I -X utf8 tools/textdb.py extract [--out translation] [--only NAME ...] [--orphan-dir DIR]
        (re-running keeps every existing translation: `en`/`skip` are merged back by id when the
         Japanese is unchanged; translated records that no longer match are reported and saved to
         build/trans/orphaned_en/ - see preserve_en)
    python -I -X utf8 tools/textdb.py insert  [--tdb translation] [--out build/text]
                                              [--append] [--only NAME ...]
    python -I -X utf8 tools/textdb.py stats
"""
import argparse
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import overlay as _ov  # noqa: E402

EXTRACTED = os.path.join(ROOT, 'extracted')
FIRST_READ_BASE = 0x8C010000
ATFIRST_OVERLAYS = ['FACEMDUL.BIN', 'HELP.BIN', 'TITLE.BIN']   # BPINFO/FONT are not overlays

MARKUP_RE = re.compile(rb'#[a-z0-9]+#|@[A-Z]/|@')
TOKEN_RE = re.compile(r'<([0-9A-F]{2})>')


# ---------------------------------------------------------------- codec ----

def decode_text(b):
    """bytes -> str, lossless with encode_text."""
    out = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c == 0x0a:
            out.append('\n')
            i += 1
        elif 0x20 <= c < 0x7f:
            out.append('<3C>' if c == 0x3c else chr(c))
            i += 1
        else:
            if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc) and i + 1 < n:
                try:
                    ch = b[i:i + 2].decode('cp932')
                    if len(ch) == 1 and ch.encode('cp932') == b[i:i + 2] and ch != '<' \
                            and ch >= 'Ā' and ch != '\n':
                        out.append(ch)
                        i += 2
                        continue
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass
            elif 0xa1 <= c <= 0xdf:
                out.append(chr(0xff61 + c - 0xa1))
                i += 1
                continue
            out.append('<%02X>' % c)
            i += 1
    return ''.join(out)


def encode_text(s):
    """str -> bytes (inverse of decode_text; also accepts plain ASCII 'en' text)."""
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(s):
        out += _enc_plain(s[pos:m.start()])
        out.append(int(m.group(1), 16))
        pos = m.end()
    out += _enc_plain(s[pos:])
    return bytes(out)


def _enc_plain(s):
    out = bytearray()
    for ch in s:
        if ch == '\n':
            out.append(0x0a)
        elif ord(ch) < 0x80:
            out.append(ord(ch))
        elif 0xff61 <= ord(ch) <= 0xff9f:
            out.append(0xa1 + ord(ch) - 0xff61)
        else:
            out += ch.encode('cp932')
    return bytes(out)


# ------------------------------------------------------- plausibility ------

def classify_text(s):
    """Scan a byte string.  Returns dict(full, ctrl, hw, bad, level2, inc_run)."""
    i, n = 0, len(s)
    full = ctrl = hw = bad = lvl2 = kana = asc = 0
    run = best = 1
    prev = -1
    for c in s:                                   # longest strictly increasing byte run
        run = run + 1 if c > prev else 1
        best = max(best, run)
        prev = c
    while i < n:
        b = s[i]
        if 0x20 <= b < 0x7f or b == 0x0a:
            asc += 0x21 <= b < 0x7f
            i += 1
        elif b < 0x20:
            ctrl += 1
            i += 1
        elif 0xa1 <= b <= 0xdf:
            hw += 1
            i += 1
        elif (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc) and i + 1 < n:
            try:
                s[i:i + 2].decode('cp932')
                ok = True
            except UnicodeDecodeError:
                ok = False
            if ok and b < 0xeb and b != 0x87:
                full += 1
                t = s[i + 1]
                if (b == 0x82 and 0x9f <= t <= 0xf1) or (b == 0x83 and 0x40 <= t <= 0x96):
                    kana += 1
                if b >= 0x99 or (b == 0x98 and s[i + 1] >= 0x9f):
                    lvl2 += 1
                i += 2
            else:
                bad += 2 if ok else 1
                i += 2 if ok else 1
        else:
            bad += 1
            i += 1
    return dict(full=full, ctrl=ctrl, hw=hw, bad=bad, level2=lvl2, inc_run=best, kana=kana, asc=asc)


def _has_image_pointer(s, base, size):
    for i in range(len(s) - 3):
        if s[i + 3] == 0x8c:
            w = s[i] | s[i + 1] << 8 | s[i + 2] << 16 | 0x8c000000
            if 0 <= w - base < size:
                return True
    return False


def accept_referenced(img, base, o, e, prev_nul):
    """Is img[o:e] (NUL at e) a Japanese text string that something points at?"""
    s = img[o:e]
    if len(s) < 2:
        return False
    c = classify_text(s)
    if c['full'] < 1 or c['bad'] or c['inc_run'] >= 8:
        return False
    if c['ctrl']:
        if c['full'] < 3 or c['ctrl'] > 4 or c['full'] * 2 < 0.5 * len(s):
            return False
        if _has_image_pointer(s, base, len(img)):
            return False
    if not c['kana']:
        # no hiragana/katakana at all: only accept kanji / half-width-kana words made of common
        # (JIS level 1) kanji, with little ASCII besides the game's @X/ #xx# markup and %d formats
        asc = c['asc'] - sum(len(m) for m in MARKUP_RE.findall(s))
        if c['level2'] * 2 > c['full'] or (c['hw'] and asc) or (asc > c['full'] + 1 and b'%' not in s):
            return False
    if not prev_nul:
        # text directly after non-NUL bytes: only accept very text-like strings
        if c['hw'] or c['level2'] or c['full'] < 2:
            return False
    return True


def accept_orphan(img, base, o, e):
    s = img[o:e]
    c = classify_text(s)
    if c['full'] < 2 or c['bad'] or c['ctrl'] or c['inc_run'] >= 6 or c['level2'] * 2 > c['full']:
        return False
    asc = c['asc']
    if c['level2'] * 3 > c['full'] or asc * 2 > c['full'] or (c['full'] == 2 and (asc or c['level2'])):
        return False
    if c['hw'] and not ((c['hw'] <= 2 and c['full'] >= 4) or (c['full'] >= 8 and c['hw'] <= c['full'])):
        return False                     # half-width kana only inside real prose
    if c['full'] * 2 < len(s) * 0.5:
        return False
    if _has_image_pointer(s, base, len(img)):
        return False
    return True


# ------------------------------------------------------------ images -------

class Image:
    """A loaded image with its base address."""

    def __init__(self, source, data, base):
        self.source = source            # e.g. 'FLOW_PRG/MEETING.BIN'
        self.data = bytes(data)
        self.base = base

    @property
    def size(self):
        return len(self.data)


def list_sources():
    """[(source path, abs path)] of every file we treat as overlay image."""
    r = []
    r.append(('1ST_READ.BIN', os.path.join(EXTRACTED, '1ST_READ.BIN')))
    for p in sorted(glob.glob(os.path.join(EXTRACTED, 'FLOW_PRG', '*.BIN'))):
        r.append(('FLOW_PRG/' + os.path.basename(p), p))
    for n in ATFIRST_OVERLAYS:
        r.append(('ATFIRST/' + n, os.path.join(EXTRACTED, 'ATFIRST', n)))
    return r


def load_image(source, path=None):
    path = path or os.path.join(EXTRACTED, *source.split('/'))
    data = open(path, 'rb').read()
    if source == '1ST_READ.BIN':
        return Image(source, data, FIRST_READ_BASE)
    info = _ov.unpack_overlay(data)
    base = info['load_addr']
    if not info['text_proven']:
        base = refine_base(data, base)
    return Image(source, data, base)


def refine_base(data, base):
    """overlay.unpack_overlay only trusts the stub literal when fewer than 10 pointers hit
    strings (GETREP.BIN, LOADBAR.BIN).  Try every 64 KiB aligned base and keep the one under
    which most distinct pointer words land on accepted Japanese strings."""
    n = len(data) // 4
    words = set(struct.unpack('<%dI' % n, data[:n * 4]))
    best = (0, base)
    for B in range(0x8C000000, 0x8D000000, 0x10000):
        k = 0
        for w in words:
            o = w - B
            if 0 < o < len(data) - 4 and data[o - 1] == 0 and 0x81 <= data[o] < 0xf0:
                e = data.find(b'\0', o)
                if e > 0 and accept_referenced(data, B, o, e, True):
                    k += 1
        if k > best[0]:
            best = (k, B)
    return best[1] if best[0] >= 10 else base


# ---------------------------------------------------------- extraction -----

class Str:
    __slots__ = ('off', 'end', 'raw', 'refs', 'interior', 'orphan', 'max_bytes', 'pad', 'pinned')

    def __init__(self, off, end, raw):
        self.off, self.end, self.raw = off, end, raw     # end = offset of terminating NUL
        self.refs = []          # offsets of pointer words that point exactly at off
        self.interior = []      # (pointer word offset, delta) pointing inside the string
        self.orphan = False
        self.max_bytes = 0
        self.pad = 0
        self.pinned = False     # part of a fixed-stride table that is not fully pointer-referenced


def find_pointers(img):
    """All aligned words that are in-image absolute pointers: {word_off: target_off}."""
    d, base, n = img.data, img.base, img.size
    cnt = n // 4
    words = struct.unpack('<%dI' % cnt, d[:cnt * 4])
    lo, hi = base, base + n
    return {i * 4: w - base for i, w in enumerate(words) if lo <= w < hi}


def extract_image(img, with_orphans=True, pad_mode='full'):
    """Return (strings sorted by offset, ptrs dict, stats dict)."""
    d, base, n = img.data, img.base, img.size
    ptrs = find_pointers(img)
    targets = {}
    for woff, t in ptrs.items():
        targets.setdefault(t, []).append(woff)
    tset = sorted(targets)

    strs = {}
    covered = bytearray(n + 1)       # bytes inside accepted strings (incl. terminator)
    # pass 1: referenced strings, smallest offset first so interior pointers attach to the
    # string that contains them
    ok_strict, ok_relaxed = set(), set()
    for t in tset:
        if t >= n - 1:
            continue
        e = d.find(b'\0', t)
        if e < 0:
            continue
        if t == 0 or d[t - 1] == 0:
            if accept_referenced(d, base, t, e, True):
                ok_strict.add(t)
        elif accept_referenced(d, base, t, e, False):
            ok_strict.add(t)
        elif accept_referenced(d, base, t, e, True):
            ok_relaxed.add(t)         # text glued to preceding bytes (record tables): see below
    # relaxed strings (not preceded by NUL; half-width kana / rare kanji) are accepted when
    # they are members of a pointer table whose neighbouring entries are accepted strings
    good = ok_strict | ok_relaxed
    for t in sorted(ok_relaxed):
        if any(((w - 4) in ptrs and ptrs[w - 4] in good) or ((w + 4) in ptrs and ptrs[w + 4] in good)
               for w in targets[t]):
            ok_strict.add(t)
    for t in tset:
        if t not in ok_strict or covered[t]:
            continue
        e = d.find(b'\0', t)
        st = Str(t, e, d[t:e])
        st.refs = sorted(targets[t])
        strs[t] = st
        for k in range(t, e + 1):
            covered[k] = 1
    # interior pointers: pointer targets inside an accepted string but not at its start
    interior_n = 0
    starts = sorted(strs)
    import bisect
    for t in tset:
        k = bisect.bisect_right(starts, t) - 1
        if k >= 0:
            s = strs[starts[k]]
            if s.off < t <= s.end:
                for w in targets[t]:
                    s.interior.append((w, t - s.off))
                    interior_n += 1
    # pointer words lying inside accepted strings are text, not pointers
    # (their refs were attached above purely by value; drop them)
    for s in strs.values():
        s.refs = [w for w in s.refs if not covered[w]]
        s.interior = [(w, dlt) for (w, dlt) in s.interior if not covered[w]]
    strs = {k: v for k, v in strs.items()}

    # pass 2: orphans
    if with_orphans:
        for m in re.finditer(rb'[^\x00]{4,}', d):
            o, e = m.start(), m.end()
            if (o and d[o - 1] != 0) or e >= n or covered[o]:
                continue
            if not (m.group()[0] >= 0x81):
                pass
            if any(covered[o:e]):
                continue
            if accept_orphan(d, base, o, e):
                st = Str(o, e, d[o:e])
                st.orphan = True
                strs[o] = st
    out = [strs[k] for k in sorted(strs)]
    mark_stride_tables(out)

    # max_bytes: string + terminator + following zero padding (see textdb docs)
    pointed = set(tset)
    nxt = None
    for i, s in enumerate(out):
        j = s.end + 1
        pad = 0
        lim = n if pad_mode == 'full' else min(n, j + ((-j) % 4))   # 'safe': alignment fill only
        while j < lim and d[j] == 0 and j not in pointed and not covered[j]:
            j += 1
            pad += 1
        s.pad = pad
        s.max_bytes = (s.end + 1 - s.off) + pad
    return out, ptrs, dict(interior=interior_n)


def mark_stride_tables(out):
    """Chains of >=3 strings at a constant spacing >= 4 where at least one member has no
    pointer are fixed-size records addressed by index: pin them (in-place only)."""
    i = 0
    n = len(out)
    while i + 2 < n:
        d = out[i + 1].off - out[i].off
        j = i + 1
        while j + 1 < n and out[j + 1].off - out[j].off == d:
            j += 1
        if d >= 4 and j - i + 1 >= 3 and any(not s.refs for s in out[i:j + 1]):
            for s in out[i:j + 1]:
                s.pinned = True
            i = j + 1
        else:
            i += 1


def ref_context(s, ptrs_by_target_words, refset):
    """Short context note for a string: where the (first) pointer lives."""
    if s.orphan:
        return 'orphan (no pointer)'
    w = s.refs[0] if s.refs else None
    if w is None:
        return ''
    run = 1
    a = w
    while (a - 4) in refset:
        a -= 4
        run += 1
    b = w
    while (b + 4) in refset:
        b += 4
        run += 1
    if run >= 3:
        return 'tbl@%x[%d/%d]' % (a, (w - a) // 4, run)
    return 'ptr@%x' % w


def build_records(img, strs, ptrs):
    refset = set()
    for s in strs:
        refset.update(s.refs)
    recs = []
    for s in strs:
        ctx = ref_context(s, None, refset)
        if s.pinned:
            ctx += ' stride-table(in-place only)'
        if s.interior:
            ctx += ' interior-ptrs=%d' % len(s.interior)
        if s.refs and len(s.refs) > 1:
            ctx += ' xrefs=%d' % len(s.refs)
        r = {'id': '%s#%x' % (img.source, s.off), 'ja': decode_text(s.raw), 'en': '',
             'max_bytes': s.max_bytes, 'refs': None if s.orphan else len(s.refs), 'ctx': ctx.strip()}
        if s.orphan:
            r['orphan'] = True
        recs.append(r)
    return recs


EXTRA_FMTS = ('hwptr', 'recarr', 'gap')      # record "fmt" values written by textfmt_hwkana / textfmt_recarray / textfmt_gap (in place only)


def extra_records(img, strs):
    """Records of the text that the pointer/orphan scan above cannot see (docs/uncovered-text.md): pointer-referenced
    half-width katakana strings (tools/textfmt_hwkana.py) and Japanese fields of fixed-stride record arrays
    (tools/textfmt_recarray.py).  They never overlap a string of `strs` nor each other.  Returned sorted by offset;
    every record carries "fmt" so that build_patch applies it in place (the repacking above never sees it)."""
    import textfmt_hwkana
    import textfmt_recarray
    ex = [(s.off, s.off + s.max_bytes) for s in strs]
    hw = textfmt_hwkana.extract(img.data, img.base, img.source, ex)
    ex2 = ex + [(_off(r), _off(r) + r['max_bytes']) for r in hw]
    ra = textfmt_recarray.extract(img.data, img.source, ex2, base=img.base)
    import textfmt_gap
    ex3 = ex2 + [(_off(r), _off(r) + r['max_bytes']) for r in ra]
    gp = textfmt_gap.extract(img.data, img.source, ex3)       # curated strings the pointer / orphan scan misses (docs/uncovered-text.md s9)
    out, end = [], -1
    for r in sorted(hw + ra + gp, key=_off):
        if _off(r) < end:
            continue                      # overlaps the previous extra record (two array readings of the same bytes)
        out.append(r)
        end = _off(r) + r['max_bytes']
    return out


def _off(rec):
    return int(rec['id'].rsplit('#', 1)[1], 16)


def jsonl_name(source):
    return source.replace('/', '__') + '.jsonl'


def write_jsonl(path, recs):
    """Atomic: the records go to <path>.tmp (same directory) which then replaces <path> (os.replace), so an interrupted
    run, a full disk or an unserialisable record never leaves a truncated or half-written database file; on failure the
    temp file is removed and the old file is untouched."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def orphan_path(orphan_dir, source):
    """Side file for the orphaned translations of one source: NAME.jsonl for the first set, then NAME.2.jsonl,
    NAME.3.jsonl ...  An earlier orphan set (translations that no longer match the image) is never overwritten."""
    base = jsonl_name(source)
    p = os.path.join(orphan_dir, base)
    k = 1
    while os.path.exists(p):
        k += 1
        p = os.path.join(orphan_dir, '%s.%d.jsonl' % (base[:-len('.jsonl')], k))
    return p


def read_jsonl(path):
    recs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


# ------------------------------------------------------- reinsertion -------

class InsertReport:
    def __init__(self, source):
        self.source = source
        self.in_place = 0
        self.relocated = 0
        self.appended = 0
        self.failed = []          # (id, needed, reason)
        self.skipped = []         # (id, reason)
        self.appended_bytes = 0
        self.translated = 0

    def line(self):
        return '%s: translated=%d in_place=%d relocated=%d appended=%d failed=%d skipped=%d +%dB' % (
            self.source, self.translated, self.in_place, self.relocated, self.appended,
            len(self.failed), len(self.skipped), self.appended_bytes)


def _en_bytes(en):
    b = encode_text(en)
    if b'\0' in b:
        raise ValueError('NUL in translation')
    return b


def _zero_runs(img, strs, minlen):
    """UNSAFE opt-in free space: zero runs >= minlen bytes outside all string regions.  They may
    be zero-initialised variables or alignment holes the code relies on (not proven)."""
    d = img.data
    taken = bytearray(len(d))
    for s in strs:
        for k in range(s.off, s.off + s.max_bytes):
            taken[k] = 1
    out, i, n = [], 0, len(d)
    while i < n:
        if d[i] == 0 and not taken[i]:
            j = i
            while j < n and d[j] == 0 and not taken[j]:
                j += 1
            if j - i >= minlen:
                a = i + 4          # keep a 4-byte margin on both sides
                z = j - 4
                if z - a > 0:
                    out.append((a, z))
            i = j
        else:
            i += 1
    return out


def insert_image(img, recs, append=False, pad_mode='full', extracted=None, zero_runs=0):
    """Apply 'en' translations.  Returns (new bytes, InsertReport).  With no translations
    the output is byte-identical to the input."""
    rep = InsertReport(img.source)
    strs, ptrs, _ = extracted or extract_image(img, pad_mode=pad_mode)
    by_off = {s.off: s for s in strs}
    buf = bytearray(img.data)
    n = img.size

    jobs = []     # (Str, bytes)
    for r in recs:
        en = r.get('en') or ''
        if not en:
            continue
        try:
            off = int(r['id'].rsplit('#', 1)[1], 16)
        except (KeyError, ValueError, IndexError):
            rep.skipped.append((r.get('id'), 'bad id'))
            continue
        s = by_off.get(off)
        if s is None:
            rep.skipped.append((r['id'], 'no string at offset (stale database?)'))
            continue
        if decode_text(s.raw) != r.get('ja'):
            rep.skipped.append((r['id'], 'ja text differs from image (stale database?)'))
            continue
        try:
            b = _en_bytes(en)
        except (ValueError, UnicodeEncodeError) as ex:
            rep.skipped.append((r['id'], 'unencodable: %s' % ex))
            continue
        jobs.append((s, b))
        rep.translated += 1
    if not jobs:
        return bytes(buf), rep

    fixed_ok, fixed_bad, movable = [], [], []
    for s, b in jobs:
        fits = len(b) + 1 <= s.max_bytes
        if s.orphan or s.interior or not s.refs or s.pinned:
            (fixed_ok if fits else fixed_bad).append((s, b))
        else:
            movable.append((s, b))
    for s, b in fixed_bad:
        rep.failed.append((img.source + '#%x' % s.off, len(b) + 1,
                           'does not fit in place (%d > %d) and cannot be relocated (%s)' % (
                               len(b) + 1, s.max_bytes,
                               'orphan' if s.orphan else 'interior pointers' if s.interior else
                               'stride table' if s.pinned else 'no refs')))

    extra = _zero_runs(img, strs, zero_runs) if zero_runs else []

    def plan(all_move):
        """Strategy A (all_move False): strings that fit stay, only overflowing ones move.
        Strategy B: every translated movable string is re-allocated inside the pooled space of
        all translated movable strings (their regions merge into large runs: far less
        fragmentation).  Returns (inplace, reloc, placed, failed)."""
        inplace = list(fixed_ok)
        reloc = []
        for s, b in movable:
            if not all_move and len(b) + 1 <= s.max_bytes:
                inplace.append((s, b))
            else:
                reloc.append((s, b))
        failed = []
        if all_move:
            # budget pruning: translating a string costs (new size - old region) extra bytes;
            # if the total demand exceeds the pooled space, leave the most expensive strings
            # in Japanese (they keep their region) instead of letting failures cascade
            pool = sum(s.max_bytes for s, b in reloc) + sum(z - a for a, z in extra) +                 sum(s.max_bytes - len(b) - 1 for s, b in inplace)
            need = sum(len(b) + 1 for s, b in reloc)
            if need > pool:
                keep = sorted(reloc, key=lambda x: (len(x[1]) + 1 - x[0].max_bytes, x[0].off))
                drop = []
                while keep and need > pool:
                    s, b = keep.pop()                  # largest extra first
                    if len(b) + 1 - s.max_bytes <= 0:
                        keep.append((s, b))
                        break
                    need -= len(b) + 1
                    pool -= s.max_bytes
                    drop.append((s, b))
                reloc = keep
                failed.extend(drop)
        while True:
            free = bytearray(n)
            for s, b in inplace:
                for k in range(s.off + len(b) + 1, s.off + s.max_bytes):
                    free[k] = 1
            for s, b in reloc:
                for k in range(s.off, s.off + s.max_bytes):
                    free[k] = 1
            fr = []
            i = 0
            while i < n:
                if free[i]:
                    j = i
                    while j < n and free[j]:
                        j += 1
                    fr.append([i, j])
                    i = j
                else:
                    i += 1
            fr.extend([a, z] for a, z in extra)
            placed = {}
            failed_now = []
            for s, b in sorted(reloc, key=lambda x: (-len(x[1]), x[0].off)):
                need = len(b) + 1
                best = None
                for r_ in fr:
                    if r_[1] - r_[0] >= need and (best is None or r_[1] - r_[0] < best[1] - best[0]):
                        best = r_
                if best is None:
                    failed_now.append((s, b))
                    continue
                placed[s.off] = best[0]
                best[0] += need
            if not failed_now:
                return inplace, reloc, placed, failed
            fset = {s.off for s, _ in failed_now}
            reloc = [(s, b) for s, b in reloc if s.off not in fset]
            for s, b in failed_now:
                if len(b) + 1 <= s.max_bytes:
                    inplace.append((s, b))          # keeps its own place after all
                else:
                    failed.append((s, b))

    planA = plan(False)
    inplace, reloc, placed, failed = planA
    if failed:
        planB = plan(True)
        if len(planB[3]) < len(failed):
            inplace, reloc, placed, failed = planB
    for s, b in failed:
        rep.failed.append((img.source + '#%x' % s.off, len(b) + 1,
                           'no free space for relocation (need %d, original %d)' % (len(b) + 1, s.max_bytes)))
    # append failures to end of image if allowed
    app_list = []
    if append:
        failed_ids = {f[0] for f in rep.failed if 'cannot be relocated' not in f[2]}
        rep.failed = [f for f in rep.failed if 'cannot be relocated' in f[2]]
        for s, b in jobs:
            if (img.source + '#%x' % s.off) in failed_ids:
                app_list.append((s, b))

    # apply: wipe freed regions of all moved strings, zero tails of in-place strings
    for s, b in inplace:
        buf[s.off:s.off + len(b)] = b
        for k in range(s.off + len(b), s.off + s.max_bytes):
            buf[k] = 0
        rep.in_place += 1
    moved = [(s, b) for s, b in reloc]
    for s, b in moved + app_list:
        for k in range(s.off, s.off + s.max_bytes):
            buf[k] = 0
    for s, b in moved:
        dst = placed[s.off]
        buf[dst:dst + len(b)] = b
        buf[dst + len(b)] = 0
        for w in s.refs:
            struct.pack_into('<I', buf, w, img.base + dst)
        rep.relocated += 1
    if app_list:
        end = len(buf)
        end += (-end) % 4
        buf.extend(b'\0' * (end - len(buf)))
        for s, b in app_list:
            dst = len(buf)
            buf.extend(b + b'\0')
            for w in s.refs:
                struct.pack_into('<I', buf, w, img.base + dst)
            rep.appended += 1
        pad = (-len(buf)) % 4
        buf.extend(b'\0' * pad)
        rep.appended_bytes = len(buf) - n
    return bytes(buf), rep


# --------------------------------------------------------------- CLI -------

def preserve_en(path, recs):
    """Carry the translations of an existing database file over to freshly extracted records.

    A record keeps its non-empty `en` (and `skip` flag) when an old record has the same id AND the same
    `ja`.  Returns (recs, orphans): `orphans` are old records with an `en` that no new record matches
    (the image changed, the id vanished or the Japanese differs): they are reported and never lost
    silently (cmd_extract saves them to a side file).  A missing `path` means nothing to preserve."""
    if not os.path.exists(path):
        return recs, []
    old = {}
    for r in read_jsonl(path):
        old[r['id']] = r
    new_by_id = {r['id']: r for r in recs}
    for r in recs:
        o = old.get(r['id'])
        if o is not None and o.get('ja') == r['ja']:
            if o.get('en'):
                r['en'] = o['en']
            if o.get('skip'):             # also kept on records without English (a skip hint is a standing decision)
                r['skip'] = True
    orphans = []
    for rid, o in old.items():
        if not o.get('en'):
            continue
        n = new_by_id.get(rid)
        if n is None or n['ja'] != o.get('ja'):
            orphans.append(o)
    return recs, orphans


def cmd_extract(args):
    total = kept = 0
    outdir = os.path.join(ROOT, args.out)
    orphan_dir = os.path.join(ROOT, args.orphan_dir)
    n_orphans = 0
    for source, path in list_sources():
        if args.only and not any(o in source for o in args.only):
            continue
        try:
            img = load_image(source, path)
        except ValueError:
            print('skip (not an overlay):', source)
            continue
        if source == '1ST_READ.BIN' and not args.with_1st_read:
            continue    # translation/ROOT__1ST_READ.BIN.jsonl belongs to another tool (textfmt_*)
        strs, ptrs, _ = extract_image(img)
        recs = build_records(img, strs, ptrs)
        if source != '1ST_READ.BIN' and not args.no_extra:
            recs = sorted(recs + extra_records(img, strs), key=_off)
        target = os.path.join(outdir, jsonl_name(source))
        recs, orphans = preserve_en(target, recs)
        if orphans:
            os.makedirs(orphan_dir, exist_ok=True)
            opath = orphan_path(orphan_dir, source)          # never overwrites an earlier orphan set
            write_jsonl(opath, orphans)
            n_orphans += len(orphans)
            print('ORPHANED: %s: %d translated records no longer match the image (ids %s%s); saved to %s' % (
                source, len(orphans), ', '.join(o['id'].rsplit('#', 1)[1] for o in orphans[:5]),
                ', ...' if len(orphans) > 5 else '', os.path.relpath(opath, ROOT)))
        if not recs:
            if os.path.exists(target):
                if orphans:
                    print('kept %s (it holds translations)' % target)
                else:
                    os.remove(target)          # no accepted strings any more: drop an outdated file
            continue
        write_jsonl(target, recs)
        total += len(recs)
        kept += sum(1 for r in recs if r.get('en'))
    print('wrote %d strings, %d translations preserved, %d orphaned' % (total, kept, n_orphans))


def cmd_insert(args):
    tdb = os.path.join(ROOT, args.tdb)
    outdir = os.path.join(ROOT, args.out)
    for source, path in list_sources():
        if args.only and not any(o in source for o in args.only):
            continue
        jp = os.path.join(tdb, jsonl_name(source))
        if not os.path.exists(jp):
            continue
        img = load_image(source, path)
        new, rep = insert_image(img, [r for r in read_jsonl(jp) if r.get('fmt') not in EXTRA_FMTS], append=args.append and source != '1ST_READ.BIN',
                                pad_mode=args.pad_mode, zero_runs=args.zero_runs)
        dst = os.path.join(outdir, *source.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new)
        print(rep.line())
        for f in rep.failed[:20]:
            print('   FAIL', f)


def cmd_stats(args):
    rows = []
    uniq = {}
    nostr = []
    tot = dict(ref=0, orph=0, chars=0, bytes=0, pinned=0, interior=0)
    for source, path in list_sources():
        try:
            img = load_image(source, path)
        except ValueError:
            continue
        strs, ptrs, st = extract_image(img)
        if not strs:
            nostr.append(source)
            continue
        ref = [s for s in strs if not s.orphan]
        orph = [s for s in strs if s.orphan]
        ja = [decode_text(s.raw) for s in strs]
        jc = sum(sum(1 for ch in t if ord(ch) > 0x7f) for t in ja)       # non-ASCII (JP) chars
        rows.append((source, len(ref), len(orph), jc, sum(len(s.raw) for s in strs),
                     sum(1 for s in strs if s.pinned), sum(1 for s in ref if s.interior)))
        for t in ja:
            uniq[t] = uniq.get(t, 0) + 1
        tot['ref'] += len(ref)
        tot['orph'] += len(orph)
        tot['chars'] += jc
        tot['bytes'] += rows[-1][4]
        tot['pinned'] += rows[-1][5]
        tot['interior'] += rows[-1][6]
    rows.sort(key=lambda r: -r[3])
    print('%-26s %7s %7s %9s %9s %6s %8s' % ('source', 'ref', 'orphan', 'JP-chars', 'raw-bytes', 'pinned', 'interior'))
    for r in rows:
        print('%-26s %7d %7d %9d %9d %6d %8d' % r)
    n = tot['ref'] + tot['orph']
    print('TOTAL %d images with text, strings=%d (referenced %d, orphan %d = %.1f%%), JP chars=%d, raw bytes=%d, '
          'pinned=%d, ref-strings with interior pointers=%d' % (
              len(rows), n, tot['ref'], tot['orph'], 100.0 * tot['orph'] / n, tot['chars'], tot['bytes'],
              tot['pinned'], tot['interior']))
    print('unique ja texts across all images: %d of %d (%.1f%%), unique JP chars: %d' % (
        len(uniq), n, 100.0 * len(uniq) / n, sum(sum(1 for ch in t if ord(ch) > 0x7f) for t in uniq)))
    print('images without any accepted string:', ' '.join(nostr))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('extract')
    p.add_argument('--out', default='translation')
    p.add_argument('--with-1st-read', action='store_true',
                   help='also write 1ST_READ.BIN.jsonl (off by default)')
    p.add_argument('--no-extra', action='store_true',
                   help='skip the half-width-katakana pointer strings and fixed-stride record-array fields '
                        '(tools/textfmt_hwkana.py, tools/textfmt_recarray.py; docs/uncovered-text.md)')
    p.add_argument('--only', nargs='*', help='only sources whose path contains one of these strings')
    p.add_argument('--orphan-dir', default='build/trans/orphaned_en',
                   help='where translated records that no longer match the image are saved')
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser('insert')
    p.add_argument('--tdb', default='translation')
    p.add_argument('--out', default='build/text')
    p.add_argument('--append', action='store_true',
                   help='append strings that do not fit to the end of the image (never for 1ST_READ.BIN)')
    p.add_argument('--pad-mode', choices=['full', 'safe'], default='full',
                   help='full: all zero bytes up to the next non-zero byte count as room (max_bytes in jsonl); '
                        'safe: only the alignment fill up to the next 4-byte boundary')
    p.add_argument('--only', nargs='*')
    p.add_argument('--zero-runs', type=int, default=0, metavar='MIN',
                   help='UNSAFE: also use zero runs >= MIN bytes outside strings as free space')
    p.set_defaults(fn=cmd_insert)
    p = sub.add_parser('stats')
    p.set_defaults(fn=cmd_stats)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == '__main__':
    main()
