# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert a Dreamcast GD-ROM dump (BIN/CUE or GDI) to cooked 2048-byte-per-sector ISO images.

Dreamcast GD-ROMs have a low-density area (tracks 1-2) and a high-density area (tracks 3..N, LBA 45000 and up).
The game's ISO9660 volume lives in the high-density area: its system area (IP.BIN) starts at LBA 45000 and the
volume size in the PVD covers everything up to the end of the disc, including the audio track in the middle
(which has no data sectors).  Two outputs are offered:

  volume (default)   ONE .iso: the whole ISO9660 volume, sector k = cooked data of LBA 45000+k, taken from whichever
                     data track holds that LBA; sectors without data (audio track area, pregaps without data) are
                     zero filled.  This is what ISO-based tools (mkisofs-style / GDI builders) call the game ISO:
                     16 system-area sectors (IP.BIN), the PVD at sector 16 and files at the LBAs the directory
                     records say, minus 45000.
  tracks             one .iso per data track (trackNN.iso), every sector of the track file cooked in file order.
                     Pregaps included, so offsets are file-relative, not LBA-relative.

Input sector layouts: MODE1/2352 (sync 12 + header 4 + 2048 data + EDC/ECC 288), MODE2/2352 (form 1: 2048 at offset
24), and 2048-byte cooked tracks (copied as they are).  Audio tracks are skipped.  Sectors are checked (sync, header
mode, MSF = LBA+150) and a summary is printed; --strict turns a bad sector into an error.

Usage:
    python -I -X utf8 tools/bincue2iso.py INPUT.cue|INPUT.gdi [OUT.iso | OUT_DIR] [--tracks] [--strict] [--force]
Never overwrites an existing output unless --force is given, and never writes next to or over the input files.
"""
import os
import re
import shlex
import sys

SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
HD_LBA = 45000
CHUNK = 4096                       # sectors per read (9.6 MB of raw data)


class DumpError(Exception):
    pass


class Track:
    def __init__(self, num, kind, path, lba, sector_size, file_offset=0, pregap_sectors=0):
        self.num, self.kind, self.path = num, kind, path           # kind: 'data' | 'audio'
        self.lba = lba                                              # LBA of the first sector OF THE FILE
        self.sector_size = sector_size                              # 2352 or 2048
        self.file_offset = file_offset
        self.pregap_sectors = pregap_sectors

    @property
    def sectors(self):
        return (os.path.getsize(self.path) - self.file_offset) // self.sector_size

    def __repr__(self):
        return "Track %d %s %s lba %d x%d" % (self.num, self.kind, os.path.basename(self.path), self.lba, self.sector_size)


def _msf(s):
    m, sec, f = (int(x) for x in s.split(":"))
    return (m * 60 + sec) * 75 + f


def parse_cue(path):
    """Tracks of a cue sheet.  The LBA of each file start follows the Redump convention for GD-ROM dumps: the low
    density area starts at 0, the high-density area at 45000, and tracks follow each other contiguously
    (file start of track N = file start of N-1 + sectors of N-1), because every file includes its own pregap."""
    base = os.path.dirname(os.path.abspath(path))
    tracks, cur_file, cur = [], None, None
    area_start = 0
    next_lba = 0
    in_hd = False
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if line.upper().startswith("REM HIGH-DENSITY"):
                in_hd = True
                next_lba = HD_LBA
            elif line.upper().startswith("FILE"):
                parts = shlex.split(line)
                cur_file = os.path.join(base, parts[1])
            elif line.upper().startswith("TRACK"):
                p = line.split()
                num, mode = int(p[1]), p[2].upper()
                if cur_file is None or not os.path.isfile(cur_file):
                    raise DumpError("track %d: file not found: %s" % (num, cur_file))
                size = 2048 if mode.endswith("/2048") else 2352
                kind = "audio" if mode == "AUDIO" else "data"
                cur = Track(num, kind, cur_file, next_lba, size)
                cur.mode = mode
                tracks.append(cur)
                next_lba += cur.sectors
    if not tracks:
        raise DumpError("no tracks in %s" % path)
    return tracks


def parse_gdi(path):
    base = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [l.strip() for l in f if l.strip()]
    n = int(lines[0])
    tracks = []
    for line in lines[1:1 + n]:
        p = shlex.split(line)
        num, lba, ctrl, ssize, name, off = int(p[0]), int(p[1]), int(p[2]), int(p[3]), p[4], int(p[5])
        fp = os.path.join(base, name)
        if not os.path.isfile(fp):
            raise DumpError("track %d: file not found: %s" % (num, fp))
        t = Track(num, "data" if ctrl == 4 else "audio", fp, lba, ssize, off)
        t.mode = "MODE1/%d" % ssize if ctrl == 4 else "AUDIO"
        tracks.append(t)
    return tracks


def load_tracks(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".cue":
        return parse_cue(path)
    if ext == ".gdi":
        return parse_gdi(path)
    raise DumpError("input must be a .cue or .gdi file")


class Stats:
    def __init__(self):
        self.sectors = self.bad_sync = self.bad_msf = self.bad_mode = self.zero = 0

    def line(self):
        return "%d sectors: %d zero, %d bad sync, %d bad MSF, %d unexpected mode" % (
            self.sectors, self.zero, self.bad_sync, self.bad_msf, self.bad_mode)


def cook(raw, size, first_lba, stats, strict, track_num):
    """Cooked 2048-byte sectors from a buffer of whole raw sectors; updates the sanity counters."""
    out = bytearray()
    n = len(raw) // size
    for i in range(n):
        s = raw[i * size:(i + 1) * size]
        stats.sectors += 1
        if size == 2048:
            out += s
            continue
        if not any(s[:16]) and not any(s[16:2064]):
            stats.zero += 1
            out += b"\x00" * 2048
            continue
        if s[:12] != SYNC:
            stats.bad_sync += 1
            if strict:
                raise DumpError("track %d sector %d: bad sync" % (track_num, first_lba + i))
        mode = s[15]
        lba = first_lba + i
        bcd = lambda b: (b >> 4) * 10 + (b & 15)
        msf = (bcd(s[12]) * 60 + bcd(s[13])) * 75 + bcd(s[14])
        if msf != lba + 150:
            stats.bad_msf += 1
            if strict:
                raise DumpError("track %d sector %d: header MSF %d != LBA+150" % (track_num, lba, msf))
        if mode == 1:
            out += s[16:2064]
        elif mode == 2:
            stats.bad_mode += 0
            out += s[24:2072]                 # form 1 only; form 2 payloads are not ISO data
        else:
            stats.bad_mode += 1
            if strict:
                raise DumpError("track %d sector %d: unexpected mode %d" % (track_num, lba, mode))
            out += s[16:2064]
    return bytes(out)


def iter_cooked(t, stats, strict):
    """(first_lba_of_chunk, cooked_bytes) over a data track file in file order."""
    with open(t.path, "rb") as f:
        f.seek(t.file_offset)
        lba = t.lba
        total = t.sectors
        done = 0
        while done < total:
            n = min(CHUNK, total - done)
            raw = f.read(n * t.sector_size)
            if len(raw) != n * t.sector_size:
                raise DumpError("%s is truncated" % t.path)
            yield lba + done, cook(raw, t.sector_size, lba + done, stats, strict, t.num)
            done += n


def write_volume(tracks, out_path, strict, hd=HD_LBA):
    data = sorted([t for t in tracks if t.kind == "data" and t.lba >= hd], key=lambda t: t.lba)
    if not data:
        raise DumpError("no high-density data tracks (LBA >= %d) found" % hd)
    end = max(t.lba + t.sectors for t in tracks if t.kind == "data" and t.lba >= hd)
    audio_end = max([t.lba + t.sectors for t in tracks if t.lba >= hd], default=end)
    total = max(end, audio_end) - hd
    stats = Stats()
    written = 0                                    # sectors written to the output so far
    with open(out_path, "wb") as out:
        for t in data:
            gap = (t.lba - hd) - written
            if gap < 0:
                raise DumpError("track %d overlaps the previous track (LBA %d)" % (t.num, t.lba))
            if gap:
                out.write(b"\x00" * 2048 * gap)
                written += gap
            for lba, cooked in iter_cooked(t, stats, strict):
                out.write(cooked)
                written += len(cooked) // 2048
        if written < total:                        # trailing audio / nothing: keep the volume length
            out.write(b"\x00" * 2048 * (total - written))
            written = total
    return written, stats


def write_tracks(tracks, out_dir, strict):
    results = []
    for t in tracks:
        if t.kind != "data":
            continue
        out_path = os.path.join(out_dir, "track%02d.iso" % t.num)
        stats = Stats()
        with open(out_path, "wb") as out:
            for lba, cooked in iter_cooked(t, stats, strict):
                out.write(cooked)
        results.append((t, out_path, stats))
    return results


# ----------------------------------------------------------------------------- cooked -> raw (patch player side)
# The reverse direction, used by apply_patch.py: after the cooked volume ISO has been patched, the raw 2352-byte
# data tracks of the player's own dump are rebuilt from it.  Sectors whose 2048 user bytes did not change are copied
# from the player's raw track as they are (so anything unusual in the dump survives); changed sectors are written as
# canonical Mode 1 sectors (sync, header with MSF = LBA + 150, user data, EDC, 8 zero bytes, P and Q parity of
# ECMA-130; the same codec as tools/discbuild.py, from which this is derived, the author's own GPL-3.0-or-later
# code).  Audio tracks and tracks the patch does not touch are never rewritten.
import struct
from operator import itemgetter

SS = 2352
USER = 2048

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
    """EDC (CRC-32, reflected polynomial 0xD8018001, init 0) of an even-length buffer."""
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
    size = major_count * minor_count
    co = []
    for k in range(minor_count):
        src = bytearray(size)
        src[(minor_inc * k) % size] = 1
        d = bytearray(2 * major_count)
        _ref_block(bytes(src), major_count, minor_count, major_mult, minor_inc, d)
        co.append(d[0])
    return co


_PCO = _coeffs(86, 24, 2, 86)
_QCO = _coeffs(52, 43, 86, 88)
_MUL = {c: _gf_mul_table(c) for c in set(_PCO) | set(_QCO)}
_qget = itemgetter(*[((m >> 1) * 86 + (m & 1) + 88 * k) % 2236 for k in range(43) for m in range(52)])


def ecc_pq(sec):
    """(P 172 bytes, Q 104 bytes) of a sector whose bytes 12..2075 are filled in (RSPC is linear over GF(256),
    so each step is one bytes.translate over a whole row)."""
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
    """A complete Mode 1 sector (2352 bytes) for 2048 user bytes at disc address `lba`."""
    if len(user) != USER:
        raise DumpError("a sector needs 2048 user bytes")
    body = bytearray(SYNC)
    body += msf_header(lba)
    body += user
    body += struct.pack("<I", edc(bytes(body)))
    body += b"\x00" * 8
    p, q = ecc_pq(body)
    body += p
    body += q
    return bytes(body)


def rebuild_raw_track(src_path, iso_path, out_path, track_lba, hd_base, out_sectors, force=(), progress=None):
    """Write the raw Mode 1 track `out_path` of `out_sectors` sectors, first sector at disc address `track_lba`, from
    the cooked volume ISO (sector k = disc LBA hd_base + k) and the player's original raw track `src_path`
    (None: nothing to copy).  A sector is copied from the original when its user bytes equal the ISO's, else it is
    encoded.  `force`: [(first_sector, count)] sector runs (counted from the start of the track file) that are
    encoded even if the user bytes are unchanged (an original all-zero sector the disc builder wrote as a real
    Mode 1 sector).  Returns the number of sectors that were encoded."""
    forced = set()
    for a, n in force:
        forced.update(range(a, a + n))
    src_n = os.path.getsize(src_path) // SS if src_path else 0
    encoded = 0
    zero = bytes(USER)
    with open(iso_path, "rb") as fi, open(out_path, "wb") as fo:
        fs = open(src_path, "rb") if src_path else None
        try:
            done = 0
            while done < out_sectors:
                n = min(CHUNK, out_sectors - done)
                first = track_lba + done
                fi.seek((first - hd_base) * USER)
                cooked = fi.read(n * USER)
                if len(cooked) != n * USER:
                    raise DumpError("the ISO ends before LBA %d" % (first + n))
                have = max(0, min(n, src_n - done))
                raw = bytearray(n * SS)
                if have:
                    fs.seek(done * SS)
                    raw[:have * SS] = fs.read(have * SS)
                    old = b"".join([bytes(raw[i * SS + 16:i * SS + 16 + USER]) for i in range(have)])
                else:
                    old = b""
                if old != cooked[:have * USER] or have < n or (forced and any(done + i in forced for i in range(n))):
                    for i in range(n):
                        if i < have and (done + i) not in forced and old[i * USER:(i + 1) * USER] == cooked[i * USER:(i + 1) * USER]:
                            continue
                        raw[i * SS:(i + 1) * SS] = encode_sector(first + i, cooked[i * USER:(i + 1) * USER])
                        encoded += 1
                fo.write(raw)
                done += n
                if progress:
                    progress(done, out_sectors)
        finally:
            if fs:
                fs.close()
    return encoded


def main(argv):
    flags = {a for a in argv[1:] if a.startswith("--")}
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args or flags - {"--tracks", "--strict", "--force"}:
        print(__doc__)
        return 2
    src = args[0]
    try:
        tracks = load_tracks(src)
        srcdir = os.path.dirname(os.path.abspath(src))
        for t in tracks:
            print("  %r  %d sectors" % (t, t.sectors))
        if "--tracks" in flags:
            out_dir = args[1] if len(args) > 1 else os.path.join(srcdir, os.path.splitext(os.path.basename(src))[0] + "_iso")
            os.makedirs(out_dir, exist_ok=True)
            for t in tracks:
                p = os.path.join(out_dir, "track%02d.iso" % t.num)
                if t.kind == "data" and os.path.exists(p) and "--force" not in flags:
                    raise DumpError("%s exists (use --force)" % p)
            for t, p, st in write_tracks(tracks, out_dir, "--strict" in flags):
                print("%s: %d bytes; %s" % (p, os.path.getsize(p), st.line()))
            return 0
        out = args[1] if len(args) > 1 else os.path.splitext(src)[0] + ".iso"
        if os.path.isdir(out):
            out = os.path.join(out, os.path.splitext(os.path.basename(src))[0] + ".iso")
        if os.path.abspath(out) in {os.path.abspath(t.path) for t in tracks} or os.path.abspath(out) == os.path.abspath(src):
            raise DumpError("the output would overwrite an input")
        if os.path.exists(out) and "--force" not in flags:
            raise DumpError("%s exists (use --force)" % out)
        sectors, st = write_volume(tracks, out, "--strict" in flags)
        print("%s: %d sectors x 2048 = %d bytes; %s" % (out, sectors, os.path.getsize(out), st.line()))
        return 0
    except (DumpError, OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
