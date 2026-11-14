"""verify_disc: structural checker for a built GD-ROM image (bin/cue + gdi).  Pure python 3 stdlib.

    python -I -X utf8 tools/verify_disc.py DIR NAME [--source DIR] [--sectors auto|all|none] [--read-files]
    python -I -X utf8 tools/verify_disc.py --original              # the repo's own Redump dump

    from verify_disc import verify_disc
    rep = verify_disc(out_dir, name, source_dir=ROOT, expect={'/X.BIN': bytes}, rewritten=sorted_lbas)
    rep.ok / rep.errors / rep.warnings / rep.text()

Checks (V-numbers refer to docs/expansion/disc-layout.md s10 and docs/disc-layout.md "verify_disc"):
  G1  gdi and cue parse, name the same files, describe the same tracks (type, LBA, sector count); files are whole sectors
  G2  geometry sound: track areas contiguous, high-density area starts at 45000, last sector below the GD-ROM ceiling 549150
      (capacity guard) - pregaps from the cue
  V3  PVD: 'CD001', 2048-byte blocks, volume space size = last LBA + 1 - 45000 (both-endian), terminator, IP.BIN signature,
      CRC-16 over 0x40..0x4F, TOC1 entries for every high-density track, first/last track, lead-out = end + 150
  V4  two independent readers agree: A = directory-record traversal from the PVD root, B = path-table driven lookup
  V5  directory records: both-endian fields, even lengths, none crossing a sector, sorted unique names, '.' and '..' right,
      sizes whole sectors; path tables L and M equal (byte-swapped), ordered (level, parent, name), size in the PVD right
  V2  every extent (system area, descriptors, path tables, directories, files) lies in ONE high-density data track after its
      pregap and below the ceiling; no two extents overlap unless identical (an alias group = shared extent)
  V7  files read through reader B have the length of their record; with `expect`, named files equal the expected bytes
  V9  every checked Mode 1 sector re-encodes to itself (sync, MSF header = LBA+150, EDC, ECC); with `source` the sectors that
      differ from the original disc are listed and (with `rewritten`) must all be in the rewritten set
  V8  free sectors are reported (count, largest holes, stale ones left by dedupe / moved extents)
"""
import bisect
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import discbuild_geom as G          # noqa: E402
import discbuild as D               # noqa: E402  (only the proven EDC/ECC codec and the constants of the original dump)

SS, USER = G.SS, 2048
ORIG_NAME = D.BASE[:-len(" (Track %d).bin")]


class Report:
    def __init__(self, label=""):
        self.label = label
        self.errors, self.warnings, self.notes = [], [], []
        self.facts = {}

    @property
    def ok(self):
        return not self.errors

    def err(self, msg):
        if len(self.errors) < 200:
            self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)

    def text(self, notes=True):
        out = ["verify_disc %s: %s (%d error(s), %d warning(s))" % (
            self.label, "OK" if self.ok else "FAILED", len(self.errors), len(self.warnings))]
        if notes:
            out += ["  " + n for n in self.notes]
        out += ["  WARNING: " + w for w in self.warnings]
        out += ["  ERROR: " + e for e in self.errors]
        return "\n".join(out)


# ------------------------------------------------------------------ raw access
class RawDisc:
    def __init__(self, geom, base):
        self.g = geom
        self.fh = {}
        for n in geom.order:
            self.fh[n] = open(os.path.join(base, geom.tracks[n].file), "rb")

    def close(self):
        for f in self.fh.values():
            f.close()

    def raw(self, lba):
        t = self.g.track_at(lba)
        if t is None:
            raise IndexError("LBA %d is outside every track" % lba)
        f = self.fh[t.no]
        f.seek((lba - t.lba) * SS)
        return f.read(SS)

    def user(self, lba, size):
        out = bytearray()
        for i in range((size + USER - 1) // USER):
            out += self.raw(lba + i)[16:16 + USER]
        return bytes(out[:size])


def _crc16(buf):
    crc = 0xFFFF
    for b in buf:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# ------------------------------------------------------------------ G: geometry, sheets
def load_geometry(base, name, rep):
    """(Geometry from the gdi or cue, or None).  Cross-checks gdi against cue when both exist."""
    gdi_p = os.path.join(base, name + ".gdi")
    cue_p = os.path.join(base, name + ".cue")
    gg = gc = None
    if os.path.exists(cue_p):
        try:
            gc = G.Geometry.from_cue(cue_p)
        except (G.GeometryError, OSError, ValueError) as e:
            rep.err("G1 cue does not parse: %s" % e)
    else:
        rep.warn("G1 no cue sheet %s" % cue_p)
    if os.path.exists(gdi_p):
        try:
            gg = G.Geometry.from_gdi(gdi_p, pregaps={n: t.pregap for n, t in gc.tracks.items()} if gc else None)
        except (G.GeometryError, OSError, ValueError) as e:
            rep.err("G1 gdi does not parse: %s" % e)
    else:
        rep.note("G1 no gdi sheet (%s); geometry taken from the cue only" % os.path.basename(gdi_p))
    if gg is None and gc is None:
        rep.err("G1 neither gdi nor cue found for %r in %s" % (name, base))
        return None
    if gg is not None and gc is not None:
        if gg.order != gc.order:
            rep.err("G1 gdi lists tracks %s, cue lists %s" % (gg.order, gc.order))
        else:
            for n in gg.order:
                a, b = gg.tracks[n], gc.tracks[n]
                if (a.kind, a.lba, a.nsec) != (b.kind, b.lba, b.nsec):
                    rep.err("G1 track %d differs: gdi %s/%d/%d sectors vs cue %s/%d/%d sectors" % (
                        n, a.kind, a.lba, a.nsec, b.kind, b.lba, b.nsec))
                if a.file != b.file:
                    rep.err("G1 track %d file: gdi %r vs cue %r" % (n, a.file, b.file))
    g = gc or gg
    if gc is not None:   # skeptic (dsk): a cue whose pregaps differ from the original disc's at identical track positions
        dflt = G.Geometry.default()
        for n in gc.order:
            d, c = dflt.tracks.get(n), gc.tracks[n]
            if d is not None and (d.kind, d.lba) == (c.kind, c.lba) and d.pregap != c.pregap:
                rep.err("G1 cue pregap of track %d is %d sectors, the original disc has %d" % (n, c.pregap, d.pregap))
    for n in g.order:
        t = g.tracks[n]
        p = os.path.join(base, t.file)
        if not os.path.exists(p):
            rep.err("G1 track file missing: %s" % p)
            return None
        sz = os.path.getsize(p)
        if sz % SS:
            rep.err("G1 %s is %d bytes, not a whole number of 2352-byte sectors" % (t.file, sz))
        if t.nsec != sz // SS:
            t.nsec = sz // SS
    for pbm in g.check():
        rep.err("G2 " + pbm)
    return g


# ------------------------------------------------------------------ ISO9660 readers
def _rec_fields(data, pos):
    l = data[pos]
    le, be = struct.unpack_from("<I", data, pos + 2)[0], struct.unpack_from(">I", data, pos + 6)[0]
    sl, sb = struct.unpack_from("<I", data, pos + 10)[0], struct.unpack_from(">I", data, pos + 14)[0]
    vl, vb = struct.unpack_from("<H", data, pos + 28)[0], struct.unpack_from(">H", data, pos + 30)[0]
    nl = data[pos + 32]
    return l, le, be, sl, sb, vl, vb, data[pos + 25], nl, bytes(data[pos + 33:pos + 33 + nl])


def parse_directory(data, label, rep, self_ext, parent_ext):
    """Records of one directory (reader A).  Returns [(name_bytes, extent, size, isdir)] without '.' and '..'."""
    out = []
    pos, idx, last = 0, 0, None
    if len(data) % USER:
        rep.err("V5 %s: size %d is not a whole number of sectors" % (label, len(data)))
    while pos < len(data):
        l = data[pos]
        if l == 0:
            pos = (pos // USER + 1) * USER
            continue
        if pos % USER + l > USER:
            rep.err("V5 %s: record at +%d crosses a sector boundary" % (label, pos))
            break
        if l < 34 or l % 2:
            rep.err("V5 %s: record at +%d has bad length %d" % (label, pos, l))
            break
        l, le, be, sl, sb, vl, vb, flags, nl, name = _rec_fields(data, pos)
        if 33 + nl > l:
            rep.err("V5 %s: record at +%d name overruns" % (label, pos))
            break
        if le != be or sl != sb or vl != vb:
            rep.err("V5 %s: both-endian mismatch in record %r (extent %d/%d size %d/%d)" % (label, name, le, be, sl, sb))
        isdir = bool(flags & 2)
        if idx == 0:
            if name != b"\x00" or le != self_ext:
                rep.err("V5 %s: first record is not '.' pointing at the directory itself (extent %d, expected %d)" % (
                    label, le, self_ext))
        elif idx == 1:
            if name != b"\x01" or le != parent_ext:
                rep.err("V5 %s: second record is not '..' pointing at the parent (extent %d, expected %d)" % (
                    label, le, parent_ext))
        else:
            if last is not None and name <= last:
                rep.err("V5 %s: records not strictly sorted at %r after %r" % (label, name, last))
            last = name
            out.append((name, le, sl, isdir))
        idx += 1
        pos += l
    if idx < 2:
        rep.err("V5 %s: directory lacks '.' / '..'" % label)
    return out


def read_volume(disc, rep, geom):
    """Reader A + checks.  Returns a dict with dirs {path: (lba,size)}, files {path: (lba,size)}, extents, pvd, ..."""
    base = geom.hd_base
    pvd_lba = base + 16
    try:
        pvd = disc.user(pvd_lba, USER)
    except IndexError as e:
        rep.err("V3 cannot read the PVD: %s" % e)
        return None
    if pvd[0] != 1 or pvd[1:6] != b"CD001" or pvd[6] != 1:
        rep.err("V3 no ISO9660 primary volume descriptor at LBA %d" % pvd_lba)
        return None
    vol = {"pvd": pvd, "dirs": {}, "files": {}, "extents": [], "dirparent": {}}
    bs = struct.unpack_from("<H", pvd, 128)[0]
    if bs != USER or struct.unpack_from(">H", pvd, 130)[0] != USER:
        rep.err("V3 logical block size %d, expected 2048" % bs)
    vsl, vsb = struct.unpack_from("<I", pvd, 80)[0], struct.unpack_from(">I", pvd, 84)[0]
    if vsl != vsb:
        rep.err("V3 volume space size both-endian mismatch %d / %d" % (vsl, vsb))
    vol["volsize"] = vsl
    if vsl != geom.end_lba - base:
        rep.err("V3 PVD volume space size %d, but the tracks end at LBA %d (expected %d)" % (vsl, geom.end_lba, geom.end_lba - base))
    # descriptor set
    l, sawterm = pvd_lba, False
    while True:
        try:
            d = disc.user(l, USER)
        except IndexError:
            break
        vol["extents"].append((l, 1, "volume descriptor %d" % d[0]))
        l += 1
        if d[0] == 255:
            sawterm = True
            break
        if l > pvd_lba + 8:
            break
    if not sawterm:
        rep.err("V3 volume descriptor set has no terminator within 8 sectors")
    vol["extents"].append((base, 16, "system area (IP.BIN)"))
    # path table info
    pts = struct.unpack_from("<I", pvd, 132)[0]
    if pts != struct.unpack_from(">I", pvd, 136)[0]:
        rep.err("V5 path table size both-endian mismatch")
    vol["pts"] = pts
    ptl = struct.unpack_from("<I", pvd, 140)[0]
    ptm = struct.unpack_from(">I", pvd, 148)[0]
    vol["ptl"], vol["ptm"] = ptl, ptm
    for nm, loc in (("L", ptl), ("M", ptm)):
        if not loc:
            rep.err("V5 path table %s location is 0" % nm)
        else:
            vol["extents"].append((loc, (pts + USER - 1) // USER, "path table " + nm))
    rootrec = pvd[156:190]
    rl, rs = struct.unpack_from("<I", rootrec, 2)[0], struct.unpack_from("<I", rootrec, 10)[0]
    if struct.unpack_from(">I", rootrec, 6)[0] != rl or struct.unpack_from(">I", rootrec, 14)[0] != rs:
        rep.err("V3 PVD root record is not both-endian consistent")
    vol["root"] = (rl, rs)
    vol["dirs"]["/"] = (rl, rs)
    vol["extents"].append((rl, (rs + USER - 1) // USER, "/"))
    stack = [("/", rl, rs, rl)]
    seen = {rl}
    while stack:
        path, lba, size, plba = stack.pop()
        try:
            data = disc.user(lba, size)
        except IndexError as e:
            rep.err("V2 directory %s unreadable: %s" % (path, e))
            continue
        ents = parse_directory(data, path, rep, lba, plba)
        for name, el, sl, isdir in ents:
            nm = name.decode("ascii", "replace")
            if not isdir:
                nm = nm.split(";")[0]
            full = (path.rstrip("/") + "/" + nm)
            if isdir:
                if el in seen:
                    rep.err("V4 directory %s reached twice (extent %d): directory loop or alias" % (full, el))
                    continue
                seen.add(el)
                vol["dirs"][full] = (el, sl)
                vol["dirparent"][full] = path
                vol["extents"].append((el, (sl + USER - 1) // USER, full + "/"))
                stack.append((full, el, sl, lba))
            else:
                if full in vol["files"]:
                    rep.err("V5 duplicate file path %s" % full)
                vol["files"][full] = (el, sl)
                if sl:
                    vol["extents"].append((el, (sl + USER - 1) // USER, full))
    groups = {}
    for p, (l, s) in vol["files"].items():
        if s:
            groups.setdefault((l, (s + USER - 1) // USER), []).append(p)
    vol["alias"] = {k: v for k, v in groups.items() if len(v) > 1}      # files sharing one extent
    return vol


def read_path_tables(disc, rep, vol):
    """Reader B: parse path tables L and M, check them, and return {dir path: extent} + directory contents by PT extent."""
    pts = vol["pts"]
    tabs = {}
    for nm, loc, e in (("L", vol["ptl"], "<"), ("M", vol["ptm"], ">")):
        try:
            data = disc.user(loc, (pts + USER - 1) // USER * USER)
        except IndexError as ex:
            rep.err("V5 path table %s unreadable: %s" % (nm, ex))
            return None
        if any(data[pts:]):
            rep.warn("V5 path table %s has non-zero bytes after its size" % nm)
        ents, pos = [], 0
        while pos < pts:
            ln = data[pos]
            if ln == 0:
                rep.err("V5 path table %s: zero-length entry at +%d" % (nm, pos))
                break
            ext = struct.unpack_from(e + "I", data, pos + 2)[0]
            par = struct.unpack_from(e + "H", data, pos + 6)[0]
            ident = data[pos + 8:pos + 8 + ln]
            ents.append((ext, par, bytes(ident)))
            pos += 8 + ln + (ln & 1)
        if pos != pts:
            rep.err("V5 path table %s entries end at %d, PVD says size %d" % (nm, pos, pts))
        tabs[nm] = ents
    if tabs["L"] != tabs["M"]:
        rep.err("V5 path tables L and M differ (%d vs %d entries or content)" % (len(tabs["L"]), len(tabs["M"])))
    ents = tabs["L"]
    if not ents or ents[0][2] != b"\x00" or ents[0][1] != 1:
        rep.err("V5 path table does not start with the root entry")
        return None
    names = {1: "/"}
    depth = {1: 0}
    prev_key = None
    for i, (ext, par, ident) in enumerate(ents, 1):
        if i == 1:
            continue
        if par >= i or par < 1:
            rep.err("V5 path table entry %d has parent %d (must be an earlier entry)" % (i, par))
            continue
        depth[i] = depth[par] + 1
        key = (depth[i], par, ident)
        if prev_key is not None and key <= prev_key:
            rep.err("V5 path table not ordered by (level, parent, name) at entry %d %r" % (i, ident))
        prev_key = key
        names[i] = names[par].rstrip("/") + "/" + ident.decode("ascii", "replace")
    bypath = {names[i]: ents[i - 1][0] for i in names}
    return bypath


def check_volume(disc, geom, rep, vol, expect=None):
    # V4 reader A vs reader B
    pt = read_path_tables(disc, rep, vol)
    if pt is not None:
        adirs = {p: v[0] for p, v in vol["dirs"].items()}
        if adirs != pt:
            only_a = sorted(set(adirs) - set(pt))[:5]
            only_b = sorted(set(pt) - set(adirs))[:5]
            diff = sorted(p for p in set(adirs) & set(pt) if adirs[p] != pt[p])[:5]
            rep.err("V4 directory records and path tables disagree: only in records %s, only in path table %s, extent differs %s" % (
                only_a, only_b, diff))
    # V2 extents
    regions = geom.hd_regions()
    ex = sorted(vol["extents"])
    prev = None
    for st, n, lab in ex:
        if not any(a <= st and st + n <= b for a, b in regions):
            rep.err("V2 extent %s (LBA %d, %d sectors) is not wholly inside one high-density data track" % (lab, st, n))
        if st + n > geom.max_lba:
            rep.err("V2 extent %s ends at LBA %d, past the GD-ROM ceiling %d" % (lab, st + n, geom.max_lba))
        if prev is not None:
            pst, pn, plab = prev
            if st < pst + pn and not (st == pst and n == pn):
                rep.err("V2 extents overlap: %s (%d+%d) and %s (%d+%d)" % (plab, pst, pn, lab, st, n))
        if prev is None or st + n >= prev[0] + prev[1]:
            prev = (st, n, lab)
    # shared extents (aliases)
    groups = {}
    for p, (l, s) in vol["files"].items():
        if s:
            groups.setdefault((l, (s + USER - 1) // USER), []).append(p)
    alias = {k: v for k, v in groups.items() if len(v) > 1}
    vol["alias"] = alias
    vol["free"] = None
    return vol


def free_ranges(geom, vol):
    cover = sorted((st, st + n) for st, n, _ in vol["extents"])
    out = []
    for a, b in geom.hd_regions():
        cur = a
        for s, e in cover:
            if e <= cur or s >= b:
                continue
            if s > cur:
                out.append((cur, min(s, b)))
            cur = max(cur, e)
        if cur < b:
            out.append((cur, b))
    return out


class Gdfs:
    """Minimal model of how the game opens a file (docs/expansion/disc-layout.md s4): mount = PVD -> path table; open(path) =
    path-table lookup of the directory, size of the directory from its own '.' record, linear scan of the records for the
    name (case-insensitive, ';1' optional); the handle is (start LBA, byte length, sector count) - nothing else about the
    disc is consulted.  It does not use the records of the parent directories (reader B of verify_disc)."""

    def __init__(self, disc, geom):
        self.disc, self.geom = disc, geom
        pvd = disc.user(geom.hd_base + 16, USER)
        pts = struct.unpack_from("<I", pvd, 132)[0]
        ptl = struct.unpack_from("<I", pvd, 140)[0]
        data = disc.user(ptl, pts)
        ents, pos = [], 0
        while pos < pts:
            ln = data[pos]
            ext = struct.unpack_from("<I", data, pos + 2)[0]
            par = struct.unpack_from("<H", data, pos + 6)[0]
            ents.append((ext, par, bytes(data[pos + 8:pos + 8 + ln])))
            pos += 8 + ln + (ln & 1)
        names = {1: "/"}
        self.dirs = {"/": ents[0][0]}
        for i, (ext, par, ident) in enumerate(ents, 1):
            if i == 1:
                continue
            names[i] = names[par].rstrip("/") + "/" + ident.decode("ascii")
            self.dirs[names[i].upper()] = ext
        self.cache = {}

    def _scan(self, dpath):
        if dpath not in self.cache:
            ext = self.dirs[dpath]
            first = self.disc.user(ext, USER)
            size = struct.unpack_from("<I", first, 10)[0]          # '.' record: size of this directory
            data = self.disc.user(ext, size)
            out, pos = {}, 0
            while pos < len(data):
                l = data[pos]
                if l == 0:
                    pos = (pos // USER + 1) * USER
                    continue
                nl = data[pos + 32]
                nm = bytes(data[pos + 33:pos + 33 + nl])
                if nm not in (b"\x00", b"\x01"):
                    out[nm.decode("ascii").split(";")[0].upper()] = (struct.unpack_from("<I", data, pos + 2)[0],
                                                                    struct.unpack_from("<I", data, pos + 10)[0])
                pos += l
            self.cache[dpath] = out
        return self.cache[dpath]

    def open(self, path):
        p = "/" + path.replace("\\", "/").strip("/").upper().split(";")[0]
        d, _, name = p.rpartition("/")
        ent = self._scan(d or "/").get(name)
        if ent is None:
            raise FileNotFoundError(path)
        return ent[0], ent[1], (ent[1] + USER - 1) // USER

    def read(self, handle):
        return self.disc.user(handle[0], handle[1])


# ------------------------------------------------------------------ sector checks
def _sector_ok(lba, raw, in_pregap):
    if len(raw) != SS:
        return False
    if raw == bytes(SS):
        return in_pregap
    return raw == D.encode_sector(lba, raw[16:16 + USER])


def _check_range(args):
    """worker: validate sectors of one file range; returns [bad lba] (first 20)"""
    path, start_lba, first, count, pre_end = args
    bad = []
    with open(path, "rb") as f:
        f.seek(first * SS)
        for i in range(first, first + count):
            raw = f.read(SS)
            lba = start_lba + i
            if not _sector_ok(lba, raw, lba < pre_end):
                bad.append(lba)
                if len(bad) >= 20:
                    break
    return bad


def check_sectors(disc, geom, base, rep, mode, source=None, rewritten=None, workers=None):
    """V9.  mode 'none' | 'auto' | 'all'.  Returns the sorted list of LBAs that differ from `source` (None without source)."""
    if mode == "none":
        return None
    full = []
    spot = set(rewritten or ())
    for n in geom.order:
        t = geom.tracks[n]
        if not t.data:
            continue
        if mode == "all" or t.nsec <= 20000:
            full.append(t)
    if full:
        jobs = []
        step = 4096
        for t in full:
            for first in range(0, t.nsec, step):
                jobs.append((os.path.join(base, t.file), t.lba, first, min(step, t.nsec - first), t.first))
        bad = []
        if mode == "all" and len(jobs) > 4:
            import multiprocessing as mp
            with mp.Pool(workers or min(16, os.cpu_count() or 4)) as pool:
                for r in pool.imap_unordered(_check_range, jobs, chunksize=1):
                    bad += r
        else:
            for j in jobs:
                bad += _check_range(j)
        nsec = sum(t.nsec for t in full)
        if bad:
            rep.err("V9 %d invalid Mode 1 sector(s) in track(s) %s, first LBAs %s" % (len(bad), [t.no for t in full], sorted(bad)[:10]))
        else:
            rep.note("V9 EDC/ECC/header OK on every sector of track(s) %s (%d sectors)" % ([t.no for t in full], nsec))
    diff = None
    if source is not None:
        sg, sdisc, sbase = source
        diff = []
        for n in geom.order:
            t = geom.tracks[n]
            st = sg.tracks.get(n)
            # sector-wise compare of the overlapping part
            nover = min(t.nsec, st.nsec) if st is not None and st.lba == t.lba else 0
            if nover:
                fa = open(os.path.join(base, t.file), "rb")
                fb = open(os.path.join(sbase, st.file), "rb")
                pos = 0
                while pos < nover:
                    cnt = min(4096, nover - pos)
                    a, b = fa.read(cnt * SS), fb.read(cnt * SS)
                    if a != b:
                        for i in range(cnt):
                            if a[i * SS:(i + 1) * SS] != b[i * SS:(i + 1) * SS]:
                                diff.append(t.lba + pos + i)
                    pos += cnt
                fa.close()
                fb.close()
            for lba in range(t.lba + nover, t.end):
                diff.append(lba)         # beyond the source track (grown track 5)
        diff.sort()
        # the differing sectors of data tracks must be valid (the rest were validated or are copies of the source)
        if mode != "all":
            for l in diff:
                tt = geom.track_at(l)
                if tt is not None and tt.data:
                    spot.add(l)
    if rewritten is not None and diff is not None:
        rs = set(rewritten)
        stray = [l for l in diff if l not in rs]
        if stray:
            rep.err("V9 %d sector(s) differ from the original disc without being part of the planned rewrite, first LBAs %s" % (
                len(stray), stray[:10]))
    if spot:
        bad = []
        for lba in sorted(spot):
            t = geom.track_at(lba)
            if t is None or not t.data:
                continue
            if mode != "all" and t in full:
                continue
            if not _sector_ok(lba, disc.raw(lba), lba < t.first):
                bad.append(lba)
        if bad:
            rep.err("V9 %d invalid rewritten/changed Mode 1 sector(s), first LBAs %s" % (len(bad), bad[:10]))
        else:
            rep.note("V9 EDC/ECC/header OK on %d changed/rewritten sector(s) outside the fully checked tracks" % len(spot))
    return diff


# ------------------------------------------------------------------ main entry
def check_ipbin(disc, geom, rep, vol):
    ip = disc.user(geom.hd_base, 16 * USER)
    if ip[:15] != b"SEGA SEGAKATANA":
        rep.err("V3 IP.BIN does not start with 'SEGA SEGAKATANA'")
        return
    want = "%04X" % _crc16(ip[0x40:0x50])
    if ip[0x20:0x24].decode("ascii", "replace") != want:
        rep.err("V3 IP.BIN CRC field %r does not match CRC-16 %s over 0x40..0x4F" % (ip[0x20:0x24], want))
    if ip[0x100:0x104] != b"TOC1":
        rep.err("V3 IP.BIN has no TOC1 block")
        return
    hd = geom.hd_data_tracks()
    allhd = [geom.tracks[n] for n in geom.order if geom.tracks[n].lba >= geom.hd_base]
    for t in allhd:
        off = 0x104 + 4 * (t.no - 3)
        got = struct.unpack_from("<I", ip, off)[0]
        want = (t.ctl << 28) | (1 << 24) | (t.first + 150)
        if got != want:
            rep.err("V3 IP.BIN TOC track %d entry 0x%08x, expected 0x%08x (FAD %d)" % (t.no, got, want, t.first + 150))
    first, last = allhd[0].no, allhd[-1].no
    for off, v in ((0x288, first), (0x28c, last)):
        got = struct.unpack_from("<I", ip, off)[0]
        if got != (0x41 << 24) | (v << 16):
            rep.err("V3 IP.BIN 0x%x = 0x%08x, expected first/last track %d" % (off, got, v))
    got = struct.unpack_from("<I", ip, 0x290)[0]
    want = (0x41 << 24) | (geom.end_lba + 150)
    if got != want:
        rep.err("V3 IP.BIN lead-out 0x%08x, expected 0x%08x (end LBA %d + 150)" % (got, want, geom.end_lba))
    boot = ip[0x60:0x70].decode("ascii", "replace").strip()
    names = {p.rsplit("/", 1)[1] for p in vol["files"] if p.count("/") == 1}
    if boot not in names:
        rep.err("V3 IP.BIN boot file %r is not in the root directory" % boot)


def open_volume(base, name, rep=None):
    rep = rep or Report(name)
    g = load_geometry(base, name, rep)
    if g is None:
        return rep, None, None, None
    disc = RawDisc(g, base)
    vol = read_volume(disc, rep, g)
    return rep, g, disc, vol


def verify_disc(out_dir, name, source_dir=None, source_name=ORIG_NAME, expect=None, rewritten=None, sectors="auto",
                read_files=False, workers=None):
    """Verify the disc <out_dir>/<name>.gdi|.cue.  Returns a Report.
    source_dir    original dump folder: differing sectors are listed and (with `rewritten`) must be planned ones
    expect        {iso path: bytes | sha1 hex str} files that must read back exactly (patched / added files)
    rewritten     iterable of LBAs the writer says it rewrote (build_disc()['rewritten_lbas'])
    sectors       'auto' (tracks of <= 20000 sectors fully + changed sectors), 'all' (every sector, multiprocess), 'none'
    read_files    also read EVERY file through reader B (size/sector sanity; slow: 1 GB)"""
    rep = Report(name)
    rep, g, disc, vol = open_volume(out_dir, name, rep)
    if g is None:
        return rep
    src = None
    try:
        if vol is None:
            return rep
        rep.note("tracks: " + g.describe())
        rep.note("end LBA %d, GD-ROM ceiling %d -> %d sector(s) of headroom" % (g.end_lba, g.max_lba, g.max_lba - g.end_lba))
        check_volume(disc, g, rep, vol)
        check_ipbin(disc, g, rep, vol)
        nfiles, ndirs = len(vol["files"]), len(vol["dirs"])
        used = sum(n for _, n, _ in vol["extents"])
        rep.note("ISO9660: %d files, %d directories, volume %d sectors, both readers (records, path tables) %s" % (
            nfiles, ndirs, vol["volsize"], "agree" if not any(e.startswith("V4") for e in rep.errors) else "DISAGREE"))
        al = vol.get("alias") or {}
        if al:
            saved = sum(n * (len(v) - 1) for (l, n), v in al.items())
            rep.note("shared extents: %d alias group(s), %d file(s) share, %d sector(s) saved" % (
                len(al), sum(len(v) for v in al.values()), saved))
        fr = free_ranges(g, vol)
        free_n = sum(b - a for a, b in fr)
        big = sorted(fr, key=lambda r: r[0] - r[1])[:3]
        stale = 0
        for a, b in fr:
            for lba in range(a, min(b, a + 100000)):
                try:
                    if any(disc.raw(lba)[16:16 + USER]):
                        stale += 1
                except IndexError:
                    pass
        rep.note("free sectors inside the high-density data tracks: %d (%d bytes), largest holes %s; %d of them hold stale data "
                 "(vacated extents; unreferenced, harmless)" % (free_n, free_n * USER, [(a, b - a) for a, b in big], stale))
        rep.facts.update(files=nfiles, dirs=ndirs, free_sectors=free_n, end_lba=g.end_lba, headroom=g.max_lba - g.end_lba,
                         alias_groups=len(al), stale_free=stale, used_sectors=used)
        # sectors
        if source_dir is not None:
            srep = Report("source")
            sg = load_geometry(source_dir, source_name, srep)
            if sg is None:
                rep.warn("source disc not readable (%s); no comparison" % "; ".join(srep.errors))
            else:
                src = (sg, RawDisc(sg, source_dir), source_dir)
        diff = check_sectors(disc, g, out_dir, rep, sectors, (src[0], src[1], source_dir) if src else None, rewritten, workers)
        if diff is not None:
            rep.note("%d sector(s) differ from the original disc (%d bytes of raw data)" % (len(diff), len(diff) * SS))
            rep.facts["diff_sectors"] = len(diff)
            # files: unchanged iff same record as the source and none of its sectors differ
            if src is not None:
                srep2 = Report("source-volume")
                svol = read_volume(src[1], srep2, src[0])
                if svol is not None:
                    changed = []
                    for p, (l, s) in vol["files"].items():
                        sv = svol["files"].get(p)
                        if sv != (l, s):
                            changed.append(p)
                            continue
                        n = (s + USER - 1) // USER
                        i = bisect.bisect_left(diff, l)
                        if i < len(diff) and diff[i] < l + n:
                            changed.append(p)
                    gone = sorted(set(svol["files"]) - set(vol["files"]))
                    new = sorted(set(vol["files"]) - set(svol["files"]))
                    rep.note("files: %d unchanged (bytes identical to the original), %d changed or moved, %d new, %d removed" % (
                        len(vol["files"]) - len(changed), len(changed) - len(new), len(new), len(gone)))
                    rep.facts.update(files_unchanged=len(vol["files"]) - len(changed), files_new=len(new))
                    if gone:
                        rep.err("V6 files missing from the disc: %s" % gone[:5])
                    vol["changed"] = set(changed)
                    # a changed file that is not announced in `expect` must still hold the SAME bytes as the original
                    # (a dedupe follower or an unpatched file that was moved); in-place changes without an announcement are errors
                    if expect is not None:
                        ex = {("/" + k.replace("\\", "/").strip("/")).upper().split(";")[0] for k in expect}
                        unexplained, repointed = [], 0
                        for p in changed:
                            if p.upper() in ex or p in new:
                                continue
                            sv = svol["files"][p]
                            if sv[0] == vol["files"][p][0]:
                                unexplained.append(p)           # same place, different sectors, not announced
                                continue
                            repointed += 1
                            a = hashlib.sha1(disc.user(*vol["files"][p])).digest()
                            b = hashlib.sha1(src[1].user(sv[0], sv[1])).digest()
                            if a != b or vol["files"][p][1] != sv[1]:
                                unexplained.append(p)
                        if unexplained:
                            rep.err("V7 %d file(s) differ from the original without being announced: %s" % (
                                len(unexplained), unexplained[:5]))
                        elif repointed:
                            rep.note("V7 %d unannounced file(s) point to another extent (dedupe) and read identical to the original" % repointed)
        # V7 expected contents
        if expect:
            bad = 0
            for k, want in sorted(expect.items()):
                key = ("/" + k.replace("\\", "/").strip("/")).upper().split(";")[0]
                hit = vol["files"].get(key)
                if hit is None:
                    rep.err("V7 expected file %s is not on the disc" % key)
                    bad += 1
                    continue
                data = disc.user(hit[0], hit[1])
                if isinstance(want, str):
                    ok = hashlib.sha1(data).hexdigest() == want.lower()
                else:
                    ok = data == want
                if not ok:
                    rep.err("V7 %s reads back with different content (record: LBA %d, %d bytes)" % (key, hit[0], hit[1]))
                    bad += 1
            if not bad:
                rep.note("V7 %d expected file(s) read back byte-identical through the directory records" % len(expect))
        if read_files:
            tot = 0
            for p, (l, s) in sorted(vol["files"].items()):
                data = disc.user(l, s)
                if len(data) != s:
                    rep.err("V7 %s: read %d of %d bytes" % (p, len(data), s))
                tot += len(data)
            rep.note("V7 all %d files read through their records (%d bytes)" % (len(vol["files"]), tot))
        return rep
    finally:
        if src:
            src[1].close()
        disc.close()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--original", action="store_true", help="verify the repo's own Redump dump (cue only)")
    ap.add_argument("--source", help="original dump folder to compare against")
    ap.add_argument("--sectors", choices=["auto", "all", "none"], default="auto")
    ap.add_argument("--read-files", action="store_true")
    a = ap.parse_args(argv)
    if a.original:
        a.dir, a.name = os.path.dirname(HERE), ORIG_NAME
    if not a.dir or not a.name:
        ap.error("DIR and NAME are required")
    rep = verify_disc(a.dir, a.name, a.source, ORIG_NAME, None, None, a.sectors, a.read_files)
    print(rep.text())
    return 0 if rep.ok else 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(main())
