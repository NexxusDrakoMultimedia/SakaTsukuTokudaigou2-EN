"""textfmt_recarray: Japanese text FIELDS inside fixed-stride record arrays of the SH-4 overlays.

Why this exists (docs/uncovered-text.md): tools/textdb.py only accepts a string that is NUL-preceded
(orphans) or pointed at (referenced).  The game keeps many name tables as arrays of fixed-size
records in which the text is a fixed-width NUL-padded field *behind a non-zero stat byte*, e.g.
    HOMETOWN.BIN   126-byte municipality records  (kanji name W=35, then the hiragana reading, then numbers)
    EVENT/ENDING/  56-byte person records         (manager / coach / foreign-player names, W=14)
    SPF_READ/SEARCH/... 60-byte records           (kanji name + half-width-katakana reading)
Records whose previous byte happened to be 0 were found as orphans, the others stayed Japanese
(the player saw 'Izu Is.<Japanese town>' and Japanese manager names in the Event list).

Detection (find_arrays) is data driven and deterministic (no per-file tables):
  1. runs   = maximal NUL-terminated cp932 text runs (kanji / kana / half-width kana / 'Family Given');
              z(run) = index of the first non-zero byte behind the run's zero padding = start of the NEXT field;
  2. strides: the histogram of z(i+j) - z(i) (j <= 3) gives candidate strides S (8..512, >= 8 hits);
  3. for a stride S the runs with equal z mod S, at most 12 slots apart, form a chain; the field width
     W = the most common (z - run start); it must hold for >= 50 % of the chain (a pool of variable strings has no mode);
  4. field k starts at z0 - W + k*S; the chain is walked slot by slot in both directions (3 misses end it) and
     every slot that holds a NUL-terminated plausible text run inside its W bytes is a member (this finds the
     fields whose run was glued to a printable stat byte or whose next field starts with a 0 byte).
`max_bytes` of every member = W (the measured slot width).  A member is only accepted when every byte between its
text and the slot end is 0, so writing a shorter text back padded with NULs never changes another field.
INFERRED upper bound: if the field behind the text always starts with a zero byte the real slot could be narrower
(`modeshare` in the ctx = share of the chain that measured W).  Arrays that are pools of pointer-referenced strings,
arrays whose members start inside a longer text run, arrays of near-identical entries and noise that merely decodes
as kana are rejected (pointer targets, glued-start share, prefix share, `good` word share).

Record: {"id": "<source>#<hexoff>", "ja", "en", "max_bytes": W, "refs": null,
         "ctx": "recarray S=56 n=205 W=14 modeshare=0.97", "fmt": "recarr"}
apply(): in place only: English bytes + NUL padding up to W; English must be <= W-1 bytes; the field is checked to
still hold `ja` before anything is written.  Nothing else in the file moves.

API: find_arrays(data) -> [Array]; extract(data, source, exclude=None) -> records; apply(data, entries) -> bytes
CLI: python -I -X utf8 tools/textfmt_recarray.py SOURCE [SOURCE..]   (prints the arrays found; paths below extracted/)
"""
import collections
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textfmt_common as C  # noqa: E402

ROOT = os.path.dirname(HERE)

DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
CH = rb'(?:' + DB + rb'|[\x20-\x7e]|[\xa1-\xdf])'
RUN = re.compile(rb'(' + CH + rb'{2,})\x00')
MIN_RUNS = 8
MAX_HOLE = 12
MIN_STRIDE, MAX_STRIDE = 8, 512
MIN_MODE_SHARE = 0.85
MIN_MEMBERS = 12
MAX_GLUED = 0.3            # members whose previous byte may belong to a text run / members (pools: ~1.0)
MIN_GOOD = 0.7             # share of members that are clearly words / names
MIN_DENSITY = 0.4          # members / slots between the first and the last member
HWRE = re.compile('[ｦ-ﾟ]')
KANARE = re.compile('[ぁ-ヿ]')
KANJIRE = re.compile('[一-鿿]')
MIXED_NAME = re.compile('^[ｦ-ﾟ・]+ [一-鿿ぁ-ヿ]+$')


REP3 = re.compile(r'(.)\1\1')          # one character three times in a row: table / code noise
REP4 = re.compile(r'(.)\1\1\1')
VOWEL_HW = re.compile('[ｱｲｳｴｵｧ-ｫｰ]')
HW_OK = re.compile(r'^[ｦ-ﾟ・]+(?: [ｦ-ﾟ・]+| [A-Z]\.?)*$')


def _level1_ratio(s):
    """share of kanji in s that are JIS level 1 (common); rare level-2 kanji dominate garbage"""
    k = l1 = 0
    for ch in s:
        if '一' <= ch <= '鿿':
            k += 1
            try:
                b = ch.encode('cp932')
            except Exception:
                continue
            if len(b) == 2 and (0x88 <= b[0] <= 0x97 or (b[0] == 0x98 and b[1] <= 0x72)):
                l1 += 1
    return 1.0 if not k else l1 / float(k)


def plausible(b):
    """Is the NUL-free byte string b a Japanese text field (name, reading, place)?  -> decoded str or None"""
    try:
        s = b.decode('cp932')
    except Exception:
        return None
    nonasc = sum(1 for ch in s if ord(ch) > 0x7f)
    if nonasc < 2 or nonasc * 2 < len(s):
        return None
    hw = len(HWRE.findall(s))
    full = nonasc - hw
    if hw and full and not MIXED_NAME.match(s):
        return None            # half-width kana mixed with kanji: only the 'foreign family + Japanese given' shape is real
    if hw and not full and REP3.search(s):
        return None
    if REP4.search(s):
        return None
    if not (KANARE.search(s) or KANJIRE.search(s) or hw):
        return None
    return s


def good(s):
    """text that is clearly a word / name (used to vet whole arrays; stricter than plausible)"""
    hw = len(HWRE.findall(s))
    if hw and hw == sum(1 for ch in s if ord(ch) > 0x7f):
        return hw >= 3 and len(set(s)) >= 3 and bool(HW_OK.match(s)) and not REP3.search(s)
    if re.match(r'^\S+ \S+$', s) and len(s) <= 12:
        return True                                  # 'Family Given'
    if KANARE.search(s):
        return True
    return _level1_ratio(s) >= 0.6


class Array:
    __slots__ = ('stride', 'width', 'members', 'runs', 'share')

    def __init__(self, stride, width, runs, share):
        self.stride, self.width, self.runs, self.share = stride, width, runs, share
        self.members = []          # [(offset, raw bytes)]

    def __repr__(self):
        return 'Array(S=%d W=%d n=%d runs=%d share=%.2f)' % (self.stride, self.width, len(self.members), self.runs, self.share)


def _runs(data):
    out = []
    n = len(data)
    for m in RUN.finditer(data):
        b = m.group(1)
        if plausible(b) is None:
            continue
        a, e = m.start(1), m.end(1)
        z = e + 1
        while z < n and data[z] == 0 and z - e <= MAX_STRIDE:
            z += 1
        if z >= n or z - e > MAX_STRIDE:
            continue
        out.append((a, e, z))
    return out


def _field(data, p, W):
    """text field at p: NUL terminated inside W bytes, plausible, and zero up to p + W (so that writing the field
    back padded with NULs can never destroy a neighbouring field) -> raw bytes or None"""
    if p < 0 or p + W > len(data):
        return None
    m = RUN.match(data, p, p + W)
    if not m or plausible(m.group(1)) is None:
        return None
    if any(data[m.end(1):p + W]):
        return None
    return m.group(1)


def _texty(b):
    """could byte b be the last byte of a text run (printable ASCII, half-width kana, or a double-byte trail)"""
    return 0x20 <= b <= 0x7e or 0xa1 <= b <= 0xdf or 0x40 <= b <= 0xfc


def pointer_targets(data, base):
    """offsets inside the image that some aligned 32-bit word points at (absolute SH-4 pointers)"""
    n = len(data) // 4
    lo, hi = base, base + len(data)
    return {w - base for w in struct.unpack('<%dI' % n, data[:n * 4]) if lo <= w < hi}


def find_arrays(data, base=None):
    """base: load address of the image; when given, arrays whose members are mostly pointer targets (pools of
    referenced strings, handled by textfmt_hwkana / textdb) are dropped."""
    tg = pointer_targets(data, base) if base else set()
    runs = _runs(data)
    if len(runs) < MIN_RUNS:
        return []
    zs = [r[2] for r in runs]
    hist = collections.Counter()
    for i in range(len(zs)):
        for j in range(i + 1, min(i + 4, len(zs))):
            d = zs[j] - zs[i]
            if MIN_STRIDE <= d <= MAX_STRIDE:
                hist[d] += 1
    arrays = []
    used = set()
    for S, cnt in hist.most_common():
        if cnt < MIN_RUNS:
            break
        by_phase = collections.defaultdict(list)
        for r in runs:
            by_phase[r[2] % S].append(r)
        for ph, lst in sorted(by_phase.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if len(lst) < MIN_RUNS:
                continue
            chains, cur = [], [lst[0]]
            for r in lst[1:]:
                if (r[2] - cur[-1][2]) // S <= MAX_HOLE + 1:
                    cur.append(r)
                else:
                    chains.append(cur)
                    cur = [r]
            chains.append(cur)
            for ch in chains:
                if len(ch) < MIN_RUNS:
                    continue
                if all(r[0] in used for r in ch):
                    continue
                cnt_w = collections.Counter(r[2] - r[0] for r in ch)
                W, wc = cnt_w.most_common(1)[0]
                share = wc / float(len(ch))
                if share < MIN_MODE_SHARE or S - W < 4 or W < 3:
                    continue          # S - W < 4: strings packed back to back (a pool), not records with other fields
                if wc < 4:
                    continue
                start0 = ch[0][2] - W
                lo = hi = start0
                p, miss = start0 - S, 0
                while p >= 0 and miss < 3:
                    if _field(data, p, W) is None:
                        miss += 1
                    else:
                        miss, lo = 0, p
                    p -= S
                p, miss = start0 + S, 0
                while p + 2 < len(data) and miss < 3:
                    if _field(data, p, W) is None:
                        miss += 1
                    else:
                        miss, hi = 0, p
                    p += S
                a = Array(S, W, len(ch), share)
                p = lo
                while p <= hi:
                    f = _field(data, p, W)
                    if f is not None and p not in used:
                        a.members.append((p, f))
                    p += S
                if len(a.members) < MIN_MEMBERS:
                    continue
                if sum(1 for _, r in a.members if good(r.decode('cp932'))) < MIN_GOOD * len(a.members):
                    continue          # table / code noise that decodes as kana
                first = collections.Counter(r[:2] for _, r in a.members)
                if first.most_common(1)[0][1] > 0.5 * len(a.members):
                    continue          # one repeated prefix: a table of near-identical entries, not names
                if len(a.members) < MIN_DENSITY * ((a.members[-1][0] - a.members[0][0]) // S + 1):
                    continue
                glued = sum(1 for o, _ in a.members if o and _texty(data[o - 1]))
                if glued > MAX_GLUED * len(a.members):
                    for o, _ in a.members:
                        used.add(o)
                    continue       # fragments of packed strings, not field starts
                if tg and sum(1 for o, _ in a.members if o in tg) * 4 >= len(a.members):
                    for o, _ in a.members:
                        used.add(o)
                    continue       # a pool of pointer-referenced strings
                for o, _ in a.members:
                    used.add(o)
                arrays.append(a)
    arrays.sort(key=lambda a: a.members[0][0])
    return arrays


def extract(data, source, exclude=None, arrays=None, base=None):
    """-> records for every array member whose slot [off, off+W) does not overlap an `exclude` byte range
    ([(a, b)] of records that already exist, e.g. textdb strings)."""
    import bisect
    if arrays is None:
        arrays = find_arrays(data, base)
    ex = sorted(exclude or [])
    starts = [a for a, _ in ex]

    def hit(a, b):
        i = max(bisect.bisect_right(starts, a) - 1, 0)
        while i < len(ex) and ex[i][0] < b:
            if ex[i][1] > a:
                return True
            i += 1
        return False

    recs = []
    for a in arrays:
        for o, raw in a.members:
            if hit(o, o + a.width):
                continue
            recs.append({'id': '%s#%x' % (source, o), 'ja': C.decode_text(raw), 'en': '', 'max_bytes': a.width,
                         'refs': None, 'ctx': 'recarray S=%d n=%d W=%d modeshare=%.2f stride-table(in-place only)' % (
                             a.stride, len(a.members), a.width, a.share), 'fmt': 'recarr'})
    return recs


def apply(data, entries):
    buf = bytearray(data)
    for e in entries:
        en = e.get('en')
        if not en:
            continue
        off = int(e['id'].rsplit('#', 1)[1], 16)
        w = e['max_bytes']
        b = C.encode_text(en)
        if len(b) > w - 1:
            raise ValueError('%s: %r is %d bytes, field holds %d' % (e['id'], en, len(b), w - 1))
        ja = C.encode_text(e['ja'])
        if bytes(buf[off:off + len(ja) + 1]) != ja + b'\x00':
            raise ValueError('%s: field no longer holds the Japanese text' % e['id'])
        buf[off:off + w] = b + b'\x00' * (w - len(b))
    return bytes(buf)


def main(argv):
    for src in argv:
        data = open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb').read()
        base = None
        try:                                   # overlays: the load address enables the pointer-pool filter
            import textdb
            base = textdb.load_image(src).base
        except Exception:
            pass
        arrs = find_arrays(data, base)
        print('%s: %d arrays' % (src, len(arrs)))
        for a in arrs:
            print('  %-52r first %#x last %#x  e.g. %s' % (a, a.members[0][0], a.members[-1][0],
                  ' | '.join(C.decode_text(r) for _, r in a.members[:3])))


if __name__ == '__main__':
    main(sys.argv[1:])
