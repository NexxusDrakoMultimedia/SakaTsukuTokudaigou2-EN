"""Dreamcast GD-ROM (Redump bin/cue) rebuilder.

API:  build_disc(patches: {iso_path: bytes}, out_dir, name, src_dir=".", strategy="gap")
Pure python 3 stdlib.  See docs/disc-layout.md for the layout rules and results.

Sector codec (ECMA-130 Mode 1, 2352 bytes):
  0..11 sync | 12..15 header (BCD min,sec,frame = LBA+150, mode=1) | 16..2063 user data
  2064..2067 EDC (CRC32, reflected poly 0xD8018001, init 0, LE) over bytes 0..2063
  2068..2075 zero | 2076..2247 P parity (172) | 2248..2351 Q parity (104)
"""
import os, re, struct, hashlib
from operator import itemgetter

SS = 2352
USER = 2048
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
BASE = "Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan) (Track %d).bin"
# (track no -> absolute LBA of the first sector of its file).  Tracks 1/2 = low-density area,
# 3/4/5 = high-density area (starts at LBA 45000).  The bin files include their pregaps.
TRACK_LBA = {1: 0, 2: 2380, 3: 45000, 4: 51342, 5: 56665}
DATA_TRACKS = (1, 3, 5)
TRACK_PREGAP = {5: 225}   # sectors of INDEX 00 at the start of the file (cue: INDEX 01 00:03:00)
PVD_LBA = 45016
HD_BASE = 45000
HD_END = 549150           # first LBA after the last sector of the GD-ROM high-density area (the disc is full here)


class DiscError(Exception):
    """Invalid request to the disc writer (bad path, duplicate name, ...)."""


class DiscFull(DiscError):
    """The content would not fit below the GD-ROM ceiling (LBA 549150 / the end of track 5)."""

# ---------------------------------------------------------------- EDC / ECC
_T8 = []
for _i in range(256):
    _e = _i
    for _ in range(8):
        _e = (_e >> 1) ^ (0xD8018001 if _e & 1 else 0)
    _T8.append(_e)
_T16 = []
for _v in range(65536):
    _s = _v
    _s = (_s >> 8) ^ _T8[_s & 0xFF]
    _s = (_s >> 8) ^ _T8[_s & 0xFF]
    _T16.append(_s)


def edc(buf):
    """EDC over buf (len must be even)."""
    e = 0
    t = _T16
    for w in struct.unpack("<%dH" % (len(buf) // 2), buf):
        e = (e >> 16) ^ t[(e ^ w) & 0xFFFF]
    return e


_F = [((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF for i in range(256)]
_B = [0] * 256
for _i in range(256):
    _B[_i ^ _F[_i]] = _i


def _ref_block(src, major_count, minor_count, major_mult, minor_inc, dest):
    """Direct transcription of the classic ecm 'ecc_computeblock' (slow reference)."""
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = _F[a]
        a = _B[_F[a] ^ b]
        dest[major] = a
        dest[major + major_count] = a ^ b


def ref_pq(sec):
    """Reference (slow) P/Q computation over sector bytes 12..; returns a new 2352-byte sector."""
    s = bytearray(sec)
    p = bytearray(172)
    _ref_block(bytes(s[12:12 + 2064]) + b"\x00" * 172, 86, 24, 2, 86, p)
    s[2076:2248] = p
    q = bytearray(104)
    _ref_block(bytes(s[12:12 + 2236]), 52, 43, 86, 88, q)
    s[2248:2352] = q
    return bytes(s)


def _gf_mul_table(c):
    out = bytearray(256)
    for x in range(256):
        r = 0
        a, b = x, c
        while b:
            if b & 1:
                r ^= a
            a = _F[a]
            b >>= 1
        out[x] = r
    return bytes(out)


def _coeffs(major_count, minor_count, major_mult, minor_inc):
    """GF(256) coefficient of each minor step, derived by feeding unit vectors to the reference."""
    size = major_count * minor_count
    co = []
    for k in range(minor_count):
        src = bytearray(size)
        src[(minor_inc * k) % size] = 1  # major 0 starts at index 0
        d = bytearray(2 * major_count)
        _ref_block(bytes(src), major_count, minor_count, major_mult, minor_inc, d)
        co.append(d[0])
    return co


_PCO = _coeffs(86, 24, 2, 86)
_QCO = _coeffs(52, 43, 86, 88)
_MUL = {c: _gf_mul_table(c) for c in set(_PCO) | set(_QCO)}
_qget = itemgetter(*[((m >> 1) * 86 + (m & 1) + 88 * k) % 2236 for k in range(43) for m in range(52)])


def ecc_pq(sec):
    """(P 172 bytes, Q 104 bytes) for a sector whose bytes 12..2075 are filled in.
    Vectorised (RSPC is linear over GF(256)); equality with ref_pq is checked in the tests."""
    src = bytes(sec[12:12 + 2064])
    fb = int.from_bytes
    a = b = 0
    for k in range(24):
        row = src[86 * k:86 * k + 86]
        a ^= fb(row.translate(_MUL[_PCO[k]]), "little")
        b ^= fb(row, "little")
    p = a.to_bytes(86, "little") + (a ^ b).to_bytes(86, "little")
    g = bytes(_qget(src + p))
    a = b = 0
    for k in range(43):
        row = g[52 * k:52 * k + 52]
        a ^= fb(row.translate(_MUL[_QCO[k]]), "little")
        b ^= fb(row, "little")
    q = a.to_bytes(52, "little") + (a ^ b).to_bytes(52, "little")
    return p, q


def msf_header(lba):
    m, r = divmod(lba + 150, 4500)
    s, f = divmod(r, 75)
    bcd = lambda x: ((x // 10) << 4) | (x % 10)
    return bytes((bcd(m), bcd(s), bcd(f), 1))


def encode_sector(lba, user):
    """Build a complete Mode 1 sector from 2048 user bytes."""
    assert len(user) == USER
    body = bytearray(SYNC)
    body += msf_header(lba)
    body += user
    body += struct.pack("<I", edc(bytes(body)))
    body += b"\x00" * 8
    p, q = ecc_pq(body)
    body += p
    body += q
    return bytes(body)


def sector_ok(lba, raw):
    """True if raw is byte-identical to the canonical Mode 1 encoding of its own user data."""
    return raw == encode_sector(lba, raw[16:16 + USER])


# ---------------------------------------------------------------- disc access
def track_path(root, name, t):
    return os.path.join(root, (name + " (Track %d).bin") % t)


class Source:
    """Read access to the original tracks by absolute LBA."""

    def __init__(self, src_dir=".", name=None):
        fmt = (name + " (Track %d).bin") if name else BASE
        self.paths = {t: os.path.join(src_dir, fmt % t) for t in TRACK_LBA}
        self.nsec = {t: os.path.getsize(p) // SS for t, p in self.paths.items()}
        self.fh = {t: open(p, "rb") for t, p in self.paths.items()}

    def close(self):
        for f in self.fh.values():
            f.close()

    def locate(self, lba):
        for t, l in TRACK_LBA.items():
            if l <= lba < l + self.nsec[t]:
                return t, lba - l
        raise IndexError(lba)

    def raw(self, lba):
        t, i = self.locate(lba)
        f = self.fh[t]
        f.seek(i * SS)
        return f.read(SS)

    def read(self, lba, size):
        out = bytearray()
        for i in range((size + USER - 1) // USER):
            out += self.raw(lba + i)[16:16 + USER]
        return bytes(out[:size])

    @property
    def end_lba(self):
        return TRACK_LBA[5] + self.nsec[5]  # first LBA after the last sector of track 5


# ---------------------------------------------------------------- ISO9660
class Rec:
    __slots__ = ("path", "dir_lba", "dir_off", "lba", "size", "isdir")

    def __repr__(self):
        return "Rec(%s lba=%d size=%d dir=%s)" % (self.path, self.lba, self.size, self.isdir)


def _walk(src, lba, size, path, out, seen):
    data = src.read(lba, size)
    pos = 0
    while pos < len(data):
        l = data[pos]
        if l == 0:
            pos = (pos // USER + 1) * USER
            continue
        r = Rec()
        r.lba, = struct.unpack_from("<I", data, pos + 2)
        r.size, = struct.unpack_from("<I", data, pos + 10)
        r.isdir = bool(data[pos + 25] & 2)
        nl = data[pos + 32]
        name = data[pos + 33:pos + 33 + nl]
        r.dir_lba = lba + pos // USER
        r.dir_off = pos % USER
        pos += l
        if name in (b"\x00", b"\x01"):
            continue
        r.path = path + "/" + name.decode("ascii", "replace").split(";")[0]
        out.append(r)
        if r.isdir and r.lba not in seen:
            seen.add(r.lba)
            _walk(src, r.lba, r.size, r.path, out, seen)


def read_filesystem(src):
    """(pvd, root_lba, root_size, [Rec ...]) - directories and files, without . and .."""
    pvd = src.read(PVD_LBA, USER)
    assert pvd[0] == 1 and pvd[1:6] == b"CD001"
    rl, = struct.unpack_from("<I", pvd, 156 + 2)
    rs, = struct.unpack_from("<I", pvd, 156 + 10)
    out = []
    _walk(src, rl, rs, "", out, {rl})
    return pvd, rl, rs, out


def _nsec(n):
    return (n + USER - 1) // USER


def _both32(v):
    return struct.pack("<I", v) + struct.pack(">I", v)


def used_extents(src, pvd, rl, rs, recs):
    """Sorted [(start_lba, nsectors, label)] of everything that occupies sectors of the volume."""
    ex = [(HD_BASE, 16, "system area (IP.BIN)")]
    l = PVD_LBA
    while True:
        d = src.read(l, USER)
        ex.append((l, 1, "volume descriptor type %d" % d[0]))
        l += 1
        if d[0] == 255:
            break
    pts, = struct.unpack_from("<I", pvd, 132)
    for off in (140, 144, 148, 152):
        pl, = struct.unpack_from("<I" if off < 148 else ">I", pvd, off)
        if pl:
            ex.append((pl, _nsec(pts), "path table @%d" % off))
    ex.append((rl, _nsec(rs), "/"))
    for r in recs:
        if r.size:
            ex.append((r.lba, _nsec(r.size), r.path + ("/" if r.isdir else "")))
    ex.sort()
    return ex


def free_gaps(ext, end_lba):
    """Unused sector ranges [[start, count]] between the used extents of the HD area."""
    gaps = []
    cur = ext[0][0] + ext[0][1]
    for s, n, _ in ext[1:]:
        if s > cur:
            gaps.append([cur, s - cur])
        cur = max(cur, s + n)
    if cur < end_lba:
        gaps.append([cur, end_lba - cur])
    # only data-track sectors are usable: drop the audio track 4 and the 225-sector pregap of track 5
    regions = [(TRACK_LBA[3], TRACK_LBA[4]), (TRACK_LBA[5] + TRACK_PREGAP[5], end_lba)]
    out = []
    for s, n in gaps:
        for a, b in regions:
            lo, hi = max(s, a), min(s + n, b)
            if hi > lo:
                out.append([lo, hi - lo])
    return out


# ---------------------------------------------------------------- planning
class Plan:
    pass


def normalise(path):
    p = path.replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p
    return p.split(";")[0].upper()


def _zero_gap(src, start, n):
    """True if all n sectors from start have all-zero user data (safe to reuse)."""
    z = bytes(USER)
    for i in range(n):
        if src.read(start + i, USER) != z:
            return False
    return True


# ---- ISO9660 metadata helpers (add file / add directory, path tables)
_NAME_RE = re.compile(r"^[A-Z0-9_]+(\.[A-Z0-9_]*)?$")


def split_iso_path(path):
    """'/EN/README.TXT' -> (['EN'], 'README.TXT'); upper-cased, validated (8.3 is the safe choice for the Sega GDFS)."""
    p = path.replace("\\", "/").split(";")[0].upper()
    parts = [x for x in p.split("/") if x]
    if not parts:
        raise DiscError("empty ISO path %r" % path)
    for x in parts:
        if not _NAME_RE.match(x) or len(x) > 30:
            raise DiscError("invalid ISO9660 name %r in %r (use A-Z 0-9 _ and at most one dot; 8.3 is safest)" % (x, path))
    return parts[:-1], parts[-1]


def make_record(lba, size, flags, ident, date):
    """ISO9660 directory record (33 + len(ident) bytes, padded to an even length), both-endian fields."""
    nl = len(ident)
    ln = 33 + nl + (1 if nl % 2 == 0 else 0)
    r = bytearray(ln)
    r[0] = ln
    struct.pack_into("<I", r, 2, lba)
    struct.pack_into(">I", r, 6, lba)
    struct.pack_into("<I", r, 10, size)
    struct.pack_into(">I", r, 14, size)
    r[18:25] = date
    r[25] = flags
    r[28:32] = b"\x01\x00\x00\x01"
    r[32] = nl
    r[33:33 + nl] = ident
    return r


def _rec_set(r, lba, size):
    struct.pack_into("<I", r, 2, lba)
    struct.pack_into(">I", r, 6, lba)
    struct.pack_into("<I", r, 10, size)
    struct.pack_into(">I", r, 14, size)


def pack_records(recs):
    """Records -> whole sectors: a record never straddles a sector boundary, zero padding after the last one."""
    out = bytearray()
    for r in recs:
        if len(out) % USER + len(r) > USER:
            out += bytes(USER - len(out) % USER)
        out += r
    if len(out) % USER or not out:
        out += bytes(USER - len(out) % USER)
    return bytes(out)


class DirModel:
    """A directory held as a list of record bytearrays (including '.' and '..') for structural edits."""

    def __init__(self, path, lba, size, data=None):
        self.path, self.lba, self.size = path, lba, size
        self.old_lba, self.old_n = lba, _nsec(size)
        self.recs, self.orig = [], {}      # orig {byte offset in the ORIGINAL directory: its record bytearray}
        pos = 0
        data = data if data is not None else b""
        while pos < len(data):
            l = data[pos]
            if l == 0:
                pos = (pos // USER + 1) * USER
                continue
            r = bytearray(data[pos:pos + l])
            self.orig[pos] = r
            self.recs.append(r)
            pos += l

    def ident(self, i):
        r = self.recs[i]
        return bytes(r[33:33 + r[32]])

    def date(self):
        return bytes(self.recs[0][18:25])

    def insert(self, rec):
        """Insert in the byte-wise sorted position among the entries after '.' and '..'."""
        key = bytes(rec[33:33 + rec[32]])
        i = 2
        while i < len(self.recs) and self.ident(i) < key:
            i += 1
        if i < len(self.recs) and self.ident(i) == key:
            raise DiscError("name %r already exists in %s" % (key, self.path))
        self.recs.insert(i, rec)

    def child_dirs(self):
        return [self.ident(i).decode("ascii") for i in range(2, len(self.recs)) if self.recs[i][25] & 2]

    def packed(self):
        return pack_records(self.recs)


def _find_rec(m, rec):
    """The record bytearray of model `m` that sat at (rec.dir_lba, rec.dir_off) in the original directory."""
    return m.orig[(rec.dir_lba - m.old_lba) * USER + rec.dir_off]


def path_table(dirs, endian):
    """ISO9660 path table.  dirs = {'/A/B': extent_lba, '/': root_lba}.  Entry order: by level, then parent number, then
    name (ECMA-119 9.4).  endian '<' (type L) or '>' (type M).  Returns bytes (not sector padded)."""
    def parent(p):
        return p.rsplit("/", 1)[0] or "/"
    order, index = ["/"], {"/": 1}
    level = ["/"]
    while level:
        nxt = []
        for p in level:
            nxt += sorted((q for q in dirs if q != "/" and parent(q) == p), key=lambda q: q.rsplit("/", 1)[1].encode())
        for q in nxt:
            order.append(q)
            index[q] = len(order)
        level = nxt
    out = bytearray()
    for p in order:
        ident = b"\x00" if p == "/" else p.rsplit("/", 1)[1].encode("ascii")
        out += bytes((len(ident), 0)) + struct.pack(endian + "I", dirs[p])
        out += struct.pack(endian + "H", index[parent(p)] if p != "/" else 1) + ident
        if len(ident) & 1:
            out += b"\x00"
    return bytes(out)


def _parent(p):
    return p.rsplit("/", 1)[0] or "/"


def plan_patches(src, patches, strategy="gap", add_files=None, add_dirs=None, dedupe=False,
                 max_lba=HD_END, allow_overflow=False, sparse=None):
    """Decide where every patched / added file goes.

    sparse {iso path: {byte offset inside the file: bytes}}   in-place edits of a file that is NOT replaced as a whole (and never
              changes size): only the sectors the edits touch are rewritten (tx5: the 630 MB /BCAST/BCAST.BIN voice archive,
              whose 26,635 subtitle headers are patched without handing 630 MB around).  Default none: output unchanged.  Plan fields: over {lba: 2048 bytes to (re)write},
    new_end (first LBA after track 5), moves [(path, old_lba, new_lba, size)], recs, extents, plus added, dedupe,
    warnings, free_after, free_sectors.

    add_files {iso path: bytes}   new files (parent directories that do not exist are created); default none
    add_dirs  [iso path]          new (empty) directories; default none
    dedupe    True: files whose FINAL bytes are identical share one extent (the lowest-LBA member keeps its extent, the others'
              directory records point to it, their old extents join the free list); default False = output unchanged
    max_lba   the GD-ROM ceiling (first LBA past the last usable sector); content that would end beyond it raises DiscFull
              unless allow_overflow (then plan.warnings says so: emulator-only, see docs/disc-layout.md)."""
    pvd, rl, rs, recs = read_filesystem(src)
    files = [r for r in recs if not r.isdir]
    bypath = {}
    for r in files:
        bypath.setdefault(r.path.upper(), []).append(r)
    ext = used_extents(src, pvd, rl, rs, recs)
    over = {}
    moves = []
    warnings = []
    new_end = src.end_lba
    free = []
    if strategy == "gap":
        # only reuse gap sectors whose content is all zero (nothing hidden that the game might read)
        for s, n in free_gaps(ext, src.end_lba):
            i = 0
            while i < n:
                if _zero_gap(src, s + i, 1):
                    j = i
                    while j < n and _zero_gap(src, s + j, 1):
                        j += 1
                    free.append([s + i, j - i])
                    i = j
                else:
                    i += 1
    by_extent = {}
    for r in files:
        if r.size:
            by_extent.setdefault(r.lba, []).append(r)
    dir_edits = {}

    def alloc(n):
        nonlocal new_end
        for fr in free:
            if fr[1] >= n:
                lba = fr[0]
                fr[0] += n
                fr[1] -= n
                return lba
        lba = new_end
        new_end += n
        return lba

    for p in sorted(patches):
        key = normalise(p)
        if key not in bypath:
            raise KeyError("no such file on disc: %s" % p)
    pmap = {}
    for p in sorted(patches, key=normalise):
        pmap[normalise(p)] = bytes(patches[p])

    # ---- directory models (only when something is added or a directory has to move)
    dirinfo = {"/": [rl, rs]}                     # dir path -> [lba, size] (updated when a directory moves)
    dirrec = {}                                   # dir path -> Rec in its parent
    for r in recs:
        if r.isdir:
            dirinfo[r.path.upper()] = [r.lba, r.size]
            dirrec[r.path.upper()] = r
    orig_dirinfo = {k: tuple(v) for k, v in dirinfo.items()}
    models = {}                                   # dir path -> DirModel
    newrec = {}                                   # added path -> the record bytearray (extent filled in later)
    added = []
    new_dir_set = []
    adds = {normalise(p): bytes(d) for p, d in (add_files or {}).items()}
    new_dirs = {normalise(p) for p in (add_dirs or [])}
    for key in list(adds) + sorted(new_dirs):
        parts, name = split_iso_path(key)
        cur = ""
        for part in parts:
            cur += "/" + part
            if cur in bypath:
                raise DiscError("%s is a file, cannot be used as a directory (%s)" % (cur, key))
            if cur not in dirinfo:
                new_dirs.add(cur)
                dirinfo[cur] = None
    for key in adds:
        if key in bypath or key in dirinfo or key in new_dirs:
            raise DiscError("%s already exists on the disc (use a patch to replace a file)" % key)
    for key in new_dirs:
        if key in bypath:
            raise DiscError("%s already exists as a file" % key)
    new_dir_list = sorted((d for d in new_dirs if dirinfo.get(d) is None), key=lambda d: (d.count("/"), d))

    def get_model(dpath):
        m = models.get(dpath)
        if m is None:
            lba, size = orig_dirinfo[dpath]
            m = models[dpath] = DirModel(dpath, lba, size, src.read(lba, size))
        return m

    structural = bool(adds or new_dir_list)
    if structural:
        for d in new_dir_list:
            par = get_model(_parent(d))
            dm = DirModel(d, 0, USER, None)
            date = par.date()
            dm.recs = [make_record(0, USER, 2, b"\x00", date), make_record(0, USER, 2, b"\x01", date)]
            models[d] = dm
            dirinfo[d] = [0, USER]
            rec = make_record(0, USER, 2, d.rsplit("/", 1)[1].encode("ascii"), date)
            par.insert(rec)
            newrec[d] = rec
        for key in sorted(adds):
            par = get_model(_parent(key))
            rec = make_record(0, 0, 0, key.rsplit("/", 1)[1].encode("ascii") + b";1", par.date())
            par.insert(rec)
            newrec[key] = rec
    # (offmap of an existing model is only valid before the first insert: patches into such a directory are looked up
    #  through the record's identity instead)
    mover = []
    for dpath, m in list(models.items()):
        n = _nsec(len(m.packed()))
        if dpath in new_dir_list:
            continue
        if n > m.old_n:
            mover.append(dpath)

    # ---- dedupe: groups of files whose final bytes are equal (needs hashing of same-size candidates only)
    followers = {}              # keeper key -> [follower Rec] (keeper itself is patched)
    alias_unpatched = []        # ([follower Rec], keeper Rec): keeper keeps its original extent
    dedupe_groups = []
    if dedupe:
        by_size = {}
        for key, rs_ in bypath.items():
            r0 = rs_[0]
            fsz = len(pmap[key]) if key in pmap else r0.size
            if fsz:
                by_size.setdefault(fsz, []).append(key)
        for fsz, keys in sorted(by_size.items()):
            if len(keys) < 2:
                continue
            groups = {}
            for key in keys:
                data = pmap[key] if key in pmap else src.read(bypath[key][0].lba, bypath[key][0].size)
                groups.setdefault(hashlib.sha1(data).digest(), []).append(key)
            for h, ks in groups.items():
                if len(ks) < 2:
                    continue
                ks.sort(key=lambda k: (bypath[k][0].lba, k))
                keeper, fol = ks[0], ks[1:]
                dedupe_groups.append((keeper, fol, fsz))
        for keeper, fol, fsz in dedupe_groups:
            kr = bypath[keeper][0]
            for fk in fol:
                fr = bypath[fk][0]
                vacated = (fr.lba, _nsec(fr.size))
                fol_rec_all = bypath[fk]
                if keeper in pmap:
                    followers.setdefault(keeper, []).extend(fol_rec_all)
                    pmap.pop(fk, None)
                else:
                    pmap.pop(fk, None)
                    alias_unpatched.append((fol_rec_all, kr))
                if strategy == "gap" and fr.lba != kr.lba and len(by_extent.get(fr.lba, [])) == 1 and vacated[1]:
                    free.append([vacated[0], vacated[1]])
        free.sort()
        # merge adjacent free ranges so that vacated neighbours form one hole
        merged = []
        for fr in free:
            if fr[1] <= 0:
                continue
            if merged and merged[-1][0] + merged[-1][1] == fr[0]:
                merged[-1][1] += fr[1]
            else:
                merged.append(list(fr))
        free[:] = merged

    # ---- metadata extents: moved directories, new directories (sectors needed are known now)
    for dpath in mover:
        m = models[dpath]
        m.size = _nsec(len(m.packed())) * USER
        m.lba = alloc(m.size // USER)
        dirinfo[dpath] = [m.lba, m.size]
    for d in new_dir_list:
        m = models[d]
        m.size = _nsec(len(m.packed())) * USER
        m.lba = alloc(m.size // USER)
        dirinfo[d] = [m.lba, m.size]
    # models needed to keep links right: the parent record of every moved directory and the '..' of its children
    for dpath in mover:
        if dpath != "/":
            get_model(_parent(dpath))
        for c in models[dpath].child_dirs():
            cp = (dpath.rstrip("/") + "/" + c)
            if cp in dirinfo:
                get_model(cp)
    # (get_model of an existing directory only ever reads the ORIGINAL bytes)
    # fix links
    for dpath, m in list(models.items()):
        lba, size = dirinfo[dpath]
        _rec_set(m.recs[0], lba, size)
        plba, psize = dirinfo[_parent(dpath)] if dpath != "/" else (lba, size)
        _rec_set(m.recs[1], plba, psize)
        if dpath != "/":
            if dpath in newrec:
                _rec_set(newrec[dpath], lba, size)
            elif dirinfo[dpath] != [dirrec[dpath].lba, dirrec[dpath].size]:
                # moved existing directory: patch the record in its parent
                pm = get_model(_parent(dpath))
                _rec_set(_find_rec(pm, dirrec[dpath]), lba, size)
    pv = bytearray(pvd)
    pv_dirty = False
    if "/" in models and dirinfo["/"] != [rl, rs]:
        struct.pack_into("<I", pv, 156 + 2, dirinfo["/"][0])
        struct.pack_into(">I", pv, 156 + 6, dirinfo["/"][0])
        struct.pack_into("<I", pv, 156 + 10, dirinfo["/"][1])
        struct.pack_into(">I", pv, 156 + 14, dirinfo["/"][1])
        pv_dirty = True

    dir_by_old = {}
    for dpath, m in models.items():
        if dpath not in new_dir_list:
            dir_by_old[(m.old_lba, m.old_n)] = m

    def model_for(dir_lba):
        for (a, n), m in dir_by_old.items():
            if a <= dir_lba < a + n:
                return m
        return None

    def set_rec(r, lba, size):
        m = model_for(r.dir_lba)
        if m is not None:
            _rec_set(_find_rec(m, r), lba, size)
            return
        ds = dir_edits.setdefault(r.dir_lba, bytearray(src.read(r.dir_lba, USER)))
        struct.pack_into("<I", ds, r.dir_off + 2, lba)
        struct.pack_into(">I", ds, r.dir_off + 6, lba)
        struct.pack_into("<I", ds, r.dir_off + 10, size)
        struct.pack_into(">I", ds, r.dir_off + 14, size)

    # unpatched dedupe aliases: the follower records simply point to the keeper's extent
    for fol_recs, kr in alias_unpatched:
        for fr in fol_recs:
            set_rec(fr, kr.lba, kr.size)

    for p, data in sorted(pmap.items()):
        key = p
        rs_ = bypath[key]
        r0 = rs_[0]
        orig_n = _nsec(r0.size)
        need = _nsec(len(data))
        old_lba = r0.lba
        shared = [r for r in by_extent.get(old_lba, []) if r.path.upper() != key]
        if need <= orig_n:
            new_lba, alloc_n = old_lba, orig_n      # in place, zero-fill the rest of the old extent
        else:
            new_lba = alloc(need)
            alloc_n = need
            moves.append((key, old_lba, new_lba, len(data)))
            if orig_n and strategy == "gap" and not shared:
                free.append([old_lba, orig_n])      # the vacated extent may be reused later
                free.sort()
        padded = data + b"\x00" * (alloc_n * USER - len(data))
        for i in range(alloc_n):
            over[new_lba + i] = padded[i * USER:(i + 1) * USER]
        for r in rs_:
            set_rec(r, new_lba, len(data))
        for r in shared:                            # aliases of the same extent follow the data
            set_rec(r, new_lba, r.size)
        for fr in followers.get(key, ()):           # dedupe followers
            set_rec(fr, new_lba, len(data))
    # ---- sparse in-place edits (never changes a size; the file must not be patched whole or moved)
    for p, edits in sorted((sparse or {}).items(), key=lambda kv: normalise(kv[0])):
        key = normalise(p)
        if key not in bypath:
            raise KeyError("no such file on disc: %s" % p)
        if key in pmap or any(key == m[0] for m in moves):
            raise DiscError("%s has a whole-file patch and a sparse patch (or moved): refused" % key)
        if any(key in [r.path.upper() for r in fl] for fl in followers.values()) or any(key == r.path.upper() for fl, _ in alias_unpatched for r in fl):
            raise DiscError("%s is a dedupe follower: a sparse patch cannot be applied to it" % key)
        r0 = bypath[key][0]
        secs = {}
        for off, b in sorted(edits.items()):
            if off < 0 or off + len(b) > r0.size:
                raise DiscError("sparse edit %s +0x%x (%d bytes) lies outside the file (%d bytes)" % (key, off, len(b), r0.size))
            pos = 0
            while pos < len(b):
                o = off + pos
                s, inner = divmod(o, USER)
                n = min(USER - inner, len(b) - pos)
                if s not in secs:
                    secs[s] = bytearray(over.get(r0.lba + s) or src.read(r0.lba + s, USER))
                secs[s][inner:inner + n] = b[pos:pos + n]
                pos += n
        for s, ba in secs.items():
            over[r0.lba + s] = bytes(ba)
    # ---- added files
    for key in sorted(adds):
        data = adds[key]
        n = max(1, _nsec(len(data)))
        lba = alloc(n)
        padded = data + b"\x00" * (n * USER - len(data))
        for i in range(n):
            over[lba + i] = padded[i * USER:(i + 1) * USER]
        _rec_set(newrec[key], lba, len(data))
        added.append((key, lba, len(data)))
    for l, ds in dir_edits.items():
        over[l] = bytes(ds)
    for dpath, m in models.items():
        blob = m.packed()
        room = dirinfo[dpath][1]
        if len(blob) > room:
            raise DiscError("internal: directory %s outgrew its extent (%d > %d)" % (dpath, len(blob), room))
        blob += bytes(room - len(blob))
        for i in range(room // USER):
            over[dirinfo[dpath][0] + i] = blob[i * USER:(i + 1) * USER]
    # ---- path tables (only when directories were added or moved)
    if new_dir_list or mover:
        dmap = {p: v[0] for p, v in dirinfo.items()}
        pts_old, = struct.unpack_from("<I", pvd, 132)
        pt_n_old = _nsec(pts_old)
        for off, endian in ((140, "<"), (148, ">")):
            blob = blob_raw = path_table(dmap, endian)
            n = _nsec(len(blob))
            old_loc, = struct.unpack_from(endian + "I", pvd, off)
            loc = old_loc if n <= pt_n_old else alloc(n)
            blob += bytes(n * USER - len(blob))
            for i in range(n):
                over[loc + i] = blob[i * USER:(i + 1) * USER]
            struct.pack_into(endian + "I", pv, off, loc)
            if off == 140:
                struct.pack_into("<I", pv, 132, len(blob_raw))
                struct.pack_into(">I", pv, 136, len(blob_raw))
        pv_dirty = True
    # ---- ceiling
    if new_end > max_lba:
        over_n = new_end - max_lba
        left = sum(f[1] for f in free)
        big = sorted((f for f in free if f[1] > 0), key=lambda f: -f[1])[:3]
        msg = ("disc full: the content ends at LBA %d, %d sector(s) = %d bytes past the GD-ROM ceiling (LBA %d; the original disc "
               "is already full to it).  Free sectors still unused inside the volume: %d (largest holes %s).  Shrink the "
               "growth, use --dedupe-files on (opt-in, frees duplicate extents), or --allow-overflow for emulator-only "
               "experiments." % (new_end, over_n, over_n * USER, max_lba, left, [tuple(f) for f in big]))
        if not allow_overflow:
            raise DiscFull(msg)
        warnings.append("OVERFLOW (emulator-only, not valid on a real GD-R): " + msg)
    if new_end != src.end_lba:
        pv[80:88] = _both32(new_end - HD_BASE)       # volume space size
        pv_dirty = True
        # IP.BIN TOC1: entry at 0x290 = lead-out (FAD LE in 3 bytes, control byte 0x41 last)
        ip = bytearray(src.read(HD_BASE, 16 * USER))
        old, = struct.unpack_from("<I", ip, 0x290)
        assert old == (0x41 << 24) | (src.end_lba + 150), hex(old)
        struct.pack_into("<I", ip, 0x290, (0x41 << 24) | (new_end + 150))
        for i in range(16):
            over[HD_BASE + i] = bytes(ip[i * USER:(i + 1) * USER])
    if pv_dirty:
        over[PVD_LBA] = bytes(pv)
    plan = Plan()
    plan.pvd, plan.recs, plan.extents = pvd, recs, ext
    plan.over, plan.new_end, plan.moves, plan.free_after = over, new_end, moves, free
    plan.added = added
    plan.new_dirs = new_dir_list
    plan.moved_dirs = [(d, dirinfo[d][0]) for d in mover]
    plan.dedupe = dedupe_groups
    plan.warnings = warnings
    plan.max_lba = max_lba
    plan.free_sectors = sum(f[1] for f in free) + max(0, max_lba - new_end)
    return plan


# ---------------------------------------------------------------- writing
CHUNK = 4096  # sectors per copy chunk (~9.6 MB)


def write_track(src, t, plan, out_path):
    """Stream track t to out_path: original sectors copied raw, overridden ones freshly encoded."""
    start = TRACK_LBA[t]
    n_orig = src.nsec[t]
    n_new = plan.new_end - start if t == 5 else n_orig
    over = sorted(l for l in plan.over if start <= l < start + n_new) if t in DATA_TRACKS else []
    if t not in DATA_TRACKS:
        assert not any(start <= l < start + n_new for l in plan.over)
    f_in = src.fh[t]
    f_in.seek(0)
    oi = 0
    with open(out_path, "wb") as fo:
        pos = 0
        while pos < n_new:
            cnt = min(CHUNK, n_new - pos)
            have = max(0, min(cnt, n_orig - pos))
            buf = bytearray(cnt * SS)
            if have:
                buf[:have * SS] = f_in.read(have * SS)
            while oi < len(over) and over[oi] < start + pos + cnt:
                l = over[oi]
                i = l - start - pos
                buf[i * SS:(i + 1) * SS] = encode_sector(l, plan.over[l])
                oi += 1
            fo.write(buf)
            pos += cnt


def cue_text(name):
    L = lambda t: '"%s (Track %d).bin"' % (name, t)
    return (
        "REM SINGLE-DENSITY AREA\r\n"
        "FILE %s BINARY\r\n  TRACK 01 MODE1/2352\r\n    INDEX 01 00:00:00\r\n"
        "FILE %s BINARY\r\n  TRACK 02 AUDIO\r\n    INDEX 00 00:00:00\r\n    INDEX 01 00:02:00\r\n"
        "REM HIGH-DENSITY AREA\r\n"
        "FILE %s BINARY\r\n  TRACK 03 MODE1/2352\r\n    INDEX 01 00:00:00\r\n"
        "FILE %s BINARY\r\n  TRACK 04 AUDIO\r\n    INDEX 00 00:00:00\r\n    INDEX 01 00:02:00\r\n"
        "FILE %s BINARY\r\n  TRACK 05 MODE1/2352\r\n    INDEX 00 00:00:00\r\n    INDEX 01 00:03:00\r\n"
        % tuple(L(t) for t in (1, 2, 3, 4, 5)))


def gdi_text(name):
    ctl = {1: 4, 2: 0, 3: 4, 4: 0, 5: 4}
    lines = ["5"]
    for t in (1, 2, 3, 4, 5):
        lines.append('%d %d %d 2352 "%s (Track %d).bin" 0' % (t, TRACK_LBA[t], ctl[t], name, t))
    return "\r\n".join(lines) + "\r\n"


class DiscSpec:
    """What to change on the disc: replaced files, added files / directories, options.
        spec = DiscSpec(patches)                       # {iso path: bytes} replacements (existing files)
        spec.add_file('/README.TXT', b'...')           # new file (missing parent directories are created)
        spec.add_directory('/EN')                      # new, empty directory
        spec.dedupe = True                             # identical files share one extent (opt-in)
        build_disc(spec, out_dir, name)"""

    def __init__(self, patches=None, dedupe=False):
        self.patches = dict(patches or {})
        self.add_files = {}
        self.add_dirs = []
        self.dedupe = dedupe

    def replace(self, path, data):
        self.patches[path] = bytes(data)
        return self

    def add_file(self, path, data):
        add_file(self, path, data)
        return self

    def add_directory(self, path):
        add_directory(self, path)
        return self


def add_file(spec, path, data):
    """Add a NEW file `path` (ISO path, A-Z 0-9 _ ., 8.3 is safest) with content `data` to the disc described by `spec`
    (a DiscSpec; a plain {path: bytes} dict is not accepted here).  Its directory record is inserted in sorted position
    (a directory that runs out of room moves to free sectors, with parent record, '.', '..', children and path tables
    kept in step); the data goes into free sectors like a relocated file.  The file is a regular, read-only extra: the
    game never opens it by itself (e.g. an on-disc README or a text pack)."""
    split_iso_path(path)
    key = normalise(path)
    if key in spec.add_files:
        raise DiscError("%s added twice" % key)
    spec.add_files[key] = bytes(data)


def add_directory(spec, path):
    split_iso_path(path)
    key = normalise(path)
    if key not in spec.add_dirs:
        spec.add_dirs.append(key)


def sparse_sha1(src_dir, iso_path, edits, name=None):
    """SHA-1 (hex) of the original file `iso_path` with the sparse `edits` {offset: bytes} applied, streamed (for verify_disc's
    `expect`: the whole-file bytes of a 630 MB archive are never held in memory)."""
    src = Source(src_dir, name)
    try:
        pvd, rl, rs, recs = read_filesystem(src)
        key = normalise(iso_path)
        rec = [r for r in recs if not r.isdir and r.path.upper() == key]
        if not rec:
            raise KeyError("no such file on disc: %s" % iso_path)
        r0 = rec[0]
        h = hashlib.sha1()
        items = sorted(edits.items())
        ei = 0
        CH = 1024 * USER
        pos = 0
        while pos < r0.size:
            n = min(CH, r0.size - pos)
            buf = bytearray(src.read(r0.lba + pos // USER, n))
            while ei < len(items) and items[ei][0] < pos + n:
                off, b = items[ei]
                if off + len(b) > pos + n:
                    raise DiscError("sparse_sha1: edit +0x%x crosses a chunk border" % off)
                buf[off - pos:off - pos + len(b)] = b
                ei += 1
            h.update(buf)
            pos += n
        return h.hexdigest()
    finally:
        src.close()


def build_disc(patches, out_dir, name, src_dir=".", strategy="gap", add_files=None, add_dirs=None, dedupe=False,
               allow_overflow=False, max_lba=HD_END, sparse=None):
    """Write '<out_dir>/<name> (Track N).bin' (N=1..5), '<name>.cue' and '<name>.gdi'.

    patches  {iso path e.g. '/FLOW_PRG/MEETING.BIN': new bytes}; paths must exist on the disc.  May also be a DiscSpec
             (then add_files / add_dirs / dedupe come from it unless given explicitly).
    strategy 'gap'    in place if the file still fits its extent, else first-fit into all-zero
                      unused sectors (or extents vacated by earlier moves), else append to track 5.
             'append' in place if it fits, else append after the last sector of track 5.
    add_files {iso path: bytes} / add_dirs [iso path]   new files / directories (default none: output unchanged)
    dedupe   identical files share one extent (default False: output unchanged)
    allow_overflow  False (default): raise DiscFull if the content would pass LBA max_lba (549150, the GD-ROM ceiling);
                    True: append past it with a warning (emulator-only experiments)
    sparse   {iso path: {offset: bytes}} in-place edits of files that are not replaced whole (see plan_patches); default none
    Returns a summary dict (adds: free_sectors, added, dedupe, warnings, rewritten_lbas, max_lba)."""
    if isinstance(patches, DiscSpec):
        spec = patches
        patches = spec.patches
        add_files = add_files if add_files is not None else spec.add_files
        add_dirs = add_dirs if add_dirs is not None else spec.add_dirs
        dedupe = dedupe or spec.dedupe
    os.makedirs(out_dir, exist_ok=True)
    src = Source(src_dir)
    try:
        # skeptic (dsk): never write over the source tracks we are reading from (--out . --name <original name>)
        for t in TRACK_LBA:
            o = track_path(out_dir, name, t)
            if os.path.exists(o) and os.path.samefile(o, src.paths[t]):
                raise DiscError("output track %s is the source track itself; choose another --out / --name" % o)
        plan = plan_patches(src, patches, strategy, add_files, add_dirs, dedupe, max_lba, allow_overflow, sparse)
        outs = {}
        for t in (1, 2, 3, 4, 5):
            outs[t] = track_path(out_dir, name, t)
            write_track(src, t, plan, outs[t])
        cue = os.path.join(out_dir, name + ".cue")
        gdi = os.path.join(out_dir, name + ".gdi")
        with open(cue, "w", newline="") as f:
            f.write(cue_text(name))
        with open(gdi, "w", newline="") as f:
            f.write(gdi_text(name))
        return {"tracks": outs, "cue": cue, "gdi": gdi, "moves": plan.moves,
                "new_end_lba": plan.new_end, "orig_end_lba": src.end_lba,
                "sectors_rewritten": len(plan.over),
                "rewritten_lbas": sorted(plan.over), "free_sectors": plan.free_sectors, "added": plan.added,
                "new_dirs": plan.new_dirs, "moved_dirs": plan.moved_dirs, "dedupe": plan.dedupe,
                "warnings": plan.warnings, "max_lba": plan.max_lba}
    finally:
        src.close()


def sha1_file(p, chunk=1 << 24):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="rebuild the disc with replacement files")
    ap.add_argument("--out", default="build/out")
    ap.add_argument("--name", default="SakaTsuku2-EN")
    ap.add_argument("--src", default=".")
    ap.add_argument("--strategy", default="gap")
    ap.add_argument("--dedupe-files", choices=["on", "off"], default="off",
                    help="on: byte-identical files share one extent (opt-in, docs/disc-layout.md)")
    ap.add_argument("--allow-overflow", action="store_true", help="allow growing past LBA 549150 (emulator-only)")
    ap.add_argument("--add-file", action="append", default=[], metavar="/ISO/PATH=local_file", help="new file on the disc")
    ap.add_argument("--add-dir", action="append", default=[], metavar="/ISO/DIR", help="new directory on the disc")
    ap.add_argument("patch", nargs="*", help="/ISO/PATH=local_file")
    a = ap.parse_args()
    pd, af = {}, {}
    for s in a.patch:
        k, v = s.split("=", 1)
        with open(v, "rb") as fh:
            pd[k] = fh.read()
    for s in a.add_file:
        k, v = s.split("=", 1)
        with open(v, "rb") as fh:
            af[k] = fh.read()
    print(build_disc(pd, a.out, a.name, a.src, a.strategy, af, a.add_dir, a.dedupe_files == "on", a.allow_overflow))
