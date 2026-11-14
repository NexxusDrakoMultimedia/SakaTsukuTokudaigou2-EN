"""textrepack: string-pool repacking for the SH-4 overlay images (docs/string-pools.md).

textdb.insert_image works per string: a translation that is longer than its own slot
(string + NUL + zero padding = Str.max_bytes) cannot use the spare bytes of a shorter neighbour.
Here the unit is the POOL: a maximal run of regions [off, off+max_bytes) of *movable* strings that
abut each other (referenced, not pinned in a stride table, no interior pointer, not an orphan).
The pool's byte range is re-laid out from scratch: every string (translated or original) is packed
back-to-back (original order), identical strings may share one copy, all pointer words that
referenced a string are rewritten.  The pool range itself never changes, so nothing outside
the pool ranges and the pointer words moves or changes.

    repack(image, load_addr, entries, ...) -> (new_image, Report)

Rules
  * entries = translation/<source>.jsonl records ({id, ja, en, ...}); 'en' empty = keep Japanese.
  * with no translation at all the image is returned unchanged (byte-identical).  Pools that are
    not touched (no translation in it, nothing moved in or out) are never rewritten.
  * strings that cannot move (orphans, pinned stride tables, interior pointers) are written in
    place when they fit, else they are listed in report.fixed_overflow (they stay Japanese).
  * if a pool is over capacity: (1) whole strings are moved to other pools that have spare
    room (cross_pool=True), (2) the remaining deficit is resolved by reverting translated strings
    to Japanese (largest growth first); these are report.overflow with their byte deficits.
  * share: 'none' (every string keeps its own copy: identical bytes as the original layout
    would have), 'dup' (strings with identical bytes inside one pool share one copy).  Sharing
    is only safe if the game never modifies such a string in place (UNKNOWN, see docs).
  * deterministic: result depends only on (image, load_addr, entries, options).
  * the image size never changes; no byte outside pool ranges, fixed-string regions and pointer
    words changes (check() proves it for a given result).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textdb as T  # noqa: E402


# ----------------------------------------------------------------- model ---

class Pool:
    __slots__ = ('idx', 'a', 'z', 'home', 'members', 'cnt', 'need', 'touched', 'deficit0')

    def __init__(self, idx, a, z):
        self.idx, self.a, self.z = idx, a, z
        self.home = []          # movable Str whose original region lies in this pool (by offset)
        self.members = []       # Str assigned to this pool after planning (home minus moved out plus moved in)
        self.cnt = {}           # sharing key -> number of members using it
        self.need = 0
        self.touched = False
        self.deficit0 = 0       # need - cap before moves/reverts (0 if it fit)

    @property
    def cap(self):
        return self.z - self.a


def is_movable(s):
    return bool(s.refs) and not (s.orphan or s.pinned or s.interior)


def find_pools(strs):
    """Maximal runs of abutting movable regions -> [Pool]; each movable Str gets its pool index in
    the returned dict {off: pool idx}."""
    mov = sorted((s for s in strs if is_movable(s)), key=lambda s: s.off)
    pools, where = [], {}
    cur = None
    for s in mov:
        if cur is not None and cur.z == s.off:
            cur.z = s.off + s.max_bytes
        else:
            cur = Pool(len(pools), s.off, s.off + s.max_bytes)
            pools.append(cur)
        cur.home.append(s)
        where[s.off] = cur.idx
    return pools, where


class Plan:
    """Result of planning (no bytes written yet)."""

    def __init__(self):
        self.pools = []
        self.where = {}          # off -> pool idx the string ends up in (movable only)
        self.cur = {}            # off -> bytes that will be stored (raw or translated)
        self.reverted = []       # [(Str, en bytes)]  translated strings that stay Japanese (pool overflow)
        self.moved = []          # [(Str, from pool, to pool)]
        self.fixed_inplace = []  # [(Str, bytes)] fixed strings translated in place
        self.fixed_overflow = [] # [(Str, bytes)] fixed strings whose English does not fit
        self.translated = 0
        self.shared_saved = 0    # bytes saved by sharing identical strings, in repacked pools


def plan_pools(strs, enc, share='dup', cross_pool=True, force=False):
    """strs: textdb Str list, enc: {off: translated bytes (no NUL)}.  Pure planning."""
    pl = Plan()
    pools, where = find_pools(strs)
    pl.pools, pl.where = pools, where
    key = (lambda s, b: b) if share == 'dup' else (lambda s, b: s.off)

    def add(p, s):
        k = key(s, pl.cur[s.off])
        if p.cnt.get(k, 0) == 0:
            p.need += len(pl.cur[s.off]) + 1
        p.cnt[k] = p.cnt.get(k, 0) + 1

    def rem(p, s):
        k = key(s, pl.cur[s.off])
        p.cnt[k] -= 1
        if p.cnt[k] == 0:
            del p.cnt[k]
            p.need -= len(pl.cur[s.off]) + 1

    for s in strs:
        b = enc.get(s.off)
        if b is None:
            continue
        pl.translated += 1
        if is_movable(s):
            pl.cur[s.off] = b
        elif len(b) + 1 <= s.max_bytes:
            pl.fixed_inplace.append((s, b))
        else:
            pl.fixed_overflow.append((s, b))
    for p in pools:
        p.members = list(p.home)
        for s in p.home:
            pl.cur.setdefault(s.off, s.raw)
            add(p, s)
        p.deficit0 = max(0, p.need - p.cap)

    # (1) cross-pool: move whole sharing groups out of deficit pools into pools with spare room
    if cross_pool and any(p.need > p.cap for p in pools):
        for p in sorted([q for q in pools if q.need > q.cap], key=lambda q: (-(q.need - q.cap), q.idx)):
            while p.need > p.cap:
                d = p.need - p.cap
                groups = {}
                for s in p.members:
                    groups.setdefault(key(s, pl.cur[s.off]), []).append(s)
                best = None            # (rank, size, off of group, recipient pool, group)
                recips = sorted((q for q in pools if q is not p and q.need < q.cap),
                                key=lambda q: (q.cap - q.need, q.idx))
                if not recips:
                    break
                for k, g in groups.items():
                    size = len(pl.cur[g[0].off]) + 1
                    for q in recips:
                        gain = 0 if k in q.cnt else size
                        if q.cap - q.need >= gain:
                            rank = (0, size) if size >= d else (1, -size)    # smallest sufficient, else largest
                            cand = (rank, min(x.off for x in g), q.idx)
                            if best is None or cand < best[0]:
                                best = (cand, g, q)
                            break
                if best is None:
                    break
                _, g, q = best
                for s in g:
                    rem(p, s)
                    p.members.remove(s)
                    q.members.append(s)
                    add(q, s)
                    pl.where[s.off] = q.idx
                    pl.moved.append((s, p.idx, q.idx))
    # (2) revert translated strings to Japanese, largest growth first, until the pool fits
    for p in pools:
        if p.need <= p.cap:
            continue
        cands = [s for s in p.members if s.off in enc and len(enc[s.off]) > len(s.raw)]
        cands.sort(key=lambda s: (-(len(enc[s.off]) - len(s.raw)), s.off))
        for s in cands:
            if p.need <= p.cap:
                break
            rem(p, s)
            pl.cur[s.off] = s.raw
            add(p, s)
            pl.reverted.append((s, enc[s.off]))
        if p.need > p.cap:                    # can only happen if translated strings shorter than raw
            cands = [s for s in p.members if s.off in enc and pl.cur[s.off] is not s.raw]
            for s in cands:
                if p.need <= p.cap:
                    break
                rem(p, s)
                pl.cur[s.off] = s.raw
                add(p, s)
                pl.reverted.append((s, enc[s.off]))
    for p in pools:
        homeset = {s.off for s in p.home}
        changed = any(pl.cur[s.off] is not s.raw for s in p.members)
        p.touched = force or changed or {s.off for s in p.members} != homeset
        if p.touched and share == 'dup':
            raw_need = sum(len(pl.cur[s.off]) + 1 for s in p.members)
            pl.shared_saved += raw_need - p.need
    return pl


# ---------------------------------------------------------------- report ---

class Report:
    def __init__(self, source):
        self.source = source
        self.translated = 0
        self.skipped = []            # (id, reason)  stale / unencodable entries
        self.pools = []              # dicts: start, end, cap, need, strings, touched, deficit0
        self.overflow = []           # dicts: id, need, orig, pool_deficit  (reverted to Japanese: pool full)
        self.fixed_overflow = []     # dicts: id, need, have, reason
        self.moved = 0               # strings moved between pools
        self.in_place_fixed = 0
        self.repacked_pools = 0
        self.shared_saved = 0
        self.ref_words = set()       # pointer words rewritten
        self.ranges = []             # byte ranges that may change [(a, z)]
        self.layout = {}             # original str off -> new off (movable strings in repacked pools)
        self.after = None            # textdb-style Str list describing the output (share='none' only)

    def line(self):
        return '%s: translated=%d pools=%d repacked=%d moved=%d overflow=%d fixed_overflow=%d fixed_inplace=%d skipped=%d' % (
            self.source, self.translated, len(self.pools), self.repacked_pools, self.moved, len(self.overflow),
            len(self.fixed_overflow), self.in_place_fixed, len(self.skipped))


def _entry_enc(entries, by_off, rep, source):
    enc = {}
    for r in entries:
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
        if T.decode_text(s.raw) != r.get('ja'):
            rep.skipped.append((r['id'], 'ja text differs from image (stale database?)'))
            continue
        try:
            b = T._en_bytes(en)
        except (ValueError, UnicodeEncodeError) as ex:
            rep.skipped.append((r['id'], 'unencodable: %s' % ex))
            continue
        enc[off] = b
    return enc


# ---------------------------------------------------------------- repack ---

def repack(image, load_addr, entries, source='', share='dup', cross_pool=True, pad_mode='full',
           extracted=None, force=False, skip_stale_check=False):
    """Apply the 'en' translations of `entries` to `image` (loaded at load_addr) with pool repacking.
    Returns (new_image bytes, Report).  `extracted` = (strs, ptrs, _) from textdb.extract_image to reuse."""
    if not source and entries:
        source = entries[0].get('id', '').rsplit('#', 1)[0]
    img = T.Image(source, image, load_addr)
    strs, ptrs, _ = extracted or T.extract_image(img, pad_mode=pad_mode)
    rep = Report(source)
    by_off = {s.off: s for s in strs}
    enc = _entry_enc(entries, by_off, rep, source)
    rep.translated = len(enc)
    pl = plan_pools(strs, enc, share=share, cross_pool=cross_pool, force=force)
    buf = bytearray(image)

    for s, b in pl.fixed_overflow:
        rep.fixed_overflow.append(dict(id='%s#%x' % (source, s.off), need=len(b) + 1, have=s.max_bytes,
                                       reason='orphan' if s.orphan else 'interior pointers' if s.interior
                                       else 'stride table' if s.pinned else 'no refs'))
    for s, b in pl.fixed_inplace:
        buf[s.off:s.off + len(b)] = b
        buf[s.off + len(b):s.off + s.max_bytes] = bytes(s.max_bytes - len(b))
        rep.ranges.append((s.off, s.off + s.max_bytes))
        rep.in_place_fixed += 1
    rep.moved = len(pl.moved)
    rep.shared_saved = pl.shared_saved
    for s, b in pl.reverted:
        p = pl.pools[pl.where[s.off]]
        rep.overflow.append(dict(id='%s#%x' % (source, s.off), need=len(b) + 1, orig=len(s.raw) + 1,
                                 pool_deficit=p.deficit0))
    for p in pl.pools:
        rep.pools.append(dict(start=p.a, end=p.z, cap=p.cap, need=p.need, strings=len(p.members),
                              touched=p.touched, deficit0=p.deficit0))
        if not p.touched:
            continue
        rep.repacked_pools += 1
        rep.ranges.append((p.a, p.z))
        buf[p.a:p.z] = bytes(p.z - p.a)
        homeset = {s.off for s in p.home}
        order = sorted(p.members, key=lambda s: (s.off not in homeset, s.off))
        pos = p.a
        addr = {}
        for s in order:
            b = pl.cur[s.off]
            k = b if share == 'dup' else s.off
            if k not in addr:
                addr[k] = pos
                buf[pos:pos + len(b)] = b
                pos += len(b) + 1                  # NUL already zero
            new = addr[k]
            rep.layout[s.off] = new
            for w in s.refs:
                struct.pack_into('<I', buf, w, load_addr + new)
                rep.ref_words.add(w)
        assert pos <= p.z, 'pool overrun'
    if share == 'none' or share is None:
        rep.after = _after(strs, pl, rep, enc)
    return bytes(buf), rep


def _after(strs, pl, rep, enc):
    """textdb-style Str list describing the OUTPUT image (share='none' only), so that a second
    repack pass can be run on the output (stability test)."""
    out = []

    def copy(s, raw=None, off=None):
        n = T.Str(s.off if off is None else off, s.end, s.raw)
        n.refs, n.interior, n.orphan, n.pinned = list(s.refs), list(s.interior), s.orphan, s.pinned
        n.pad, n.max_bytes = s.pad, s.max_bytes
        if raw is not None:
            n.raw, n.end = raw, n.off + len(raw)
        return n

    inplace = {s.off: b for s, b in pl.fixed_inplace}
    for s in strs:
        if not is_movable(s):
            out.append(copy(s, inplace.get(s.off)))
    for p in pl.pools:
        homeset = {s.off for s in p.home}
        if not p.touched:
            out.extend(copy(s) for s in p.home)
            continue
        order = sorted(p.members, key=lambda s: (s.off not in homeset, s.off))
        pos = p.a
        news = []
        for s in order:
            b = pl.cur[s.off]
            n = copy(s, b, pos)
            news.append(n)
            pos += len(b) + 1
        for i, n in enumerate(news):
            nxt = news[i + 1].off if i + 1 < len(news) else p.z
            n.max_bytes = nxt - n.off
            n.pad = n.max_bytes - (n.end + 1 - n.off)
            out.append(n)
    out.sort(key=lambda s: s.off)
    return out


# ----------------------------------------------------------------- check ---

def cstr(img, off):
    return img[off:img.index(b'\0', off)]


def check(old, new, load_addr, strs, enc, rep, share='dup'):
    """Independent proof for one repack() result.  Returns a list of problem strings (empty = ok):
      * size unchanged
      * every pointer word of every movable string resolves to the intended text (translated, or the
        original Japanese for untranslated / reverted strings)
      * every pointer word of every fixed string is unchanged and the string reads as intended
      * every changed byte lies in a pool range, a fixed-in-place region or a rewritten pointer word
    """
    bad = []
    if len(old) != len(new):
        bad.append('size changed')
        return bad
    reverted = {x['id'].rsplit('#', 1)[1] for x in rep.overflow}
    allowed = bytearray(len(old))
    for a, z in rep.ranges:
        for k in range(a, z):
            allowed[k] = 1
    for w in rep.ref_words:
        for k in range(w, w + 4):
            allowed[k] = 1
    for i in range(len(old)):
        if old[i] != new[i] and not allowed[i]:
            bad.append('byte %#x changed outside allowed ranges' % i)
            break
    fixed_over = {x['id'].rsplit('#', 1)[1] for x in rep.fixed_overflow}
    for s in strs:
        want = s.raw
        if s.off in enc and ('%x' % s.off) not in reverted and ('%x' % s.off) not in fixed_over:
            want = enc[s.off]
        if is_movable(s):
            for w in s.refs:
                p = struct.unpack_from('<I', new, w)[0] - load_addr
                if not 0 <= p < len(new) or cstr(new, p) != want:
                    bad.append('ptr@%x of str %#x resolves to %r not %r' % (
                        w, s.off, new[p:p + 12] if 0 <= p < len(new) else p, want[:12]))
                    break
        else:
            for w in s.refs:
                if old[w:w + 4] != new[w:w + 4]:
                    bad.append('fixed str %#x pointer changed' % s.off)
            if new[s.off:s.off + len(want)] != want or new[s.off + len(want)] != 0:
                bad.append('fixed str %#x text wrong' % s.off)
        if len(bad) > 20:
            break
    return bad


def load_entries(source):
    import json
    p = os.path.join(T.ROOT, 'translation', T.jsonl_name(source))
    return T.read_jsonl(p) if os.path.exists(p) else []


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', help='e.g. FLOW_PRG/MEETING.BIN')
    ap.add_argument('--out')
    ap.add_argument('--share', choices=['none', 'dup'], default='dup')
    ap.add_argument('--no-cross-pool', action='store_true')
    a = ap.parse_args(argv)
    img = T.load_image(a.source)
    new, rep = repack(img.data, img.base, load_entries(a.source), source=a.source, share=a.share,
                      cross_pool=not a.no_cross_pool)
    print(rep.line())
    for o in rep.overflow[:20]:
        print('  OVERFLOW', o)
    if a.out:
        open(a.out, 'wb').write(new)


if __name__ == '__main__':
    main()
