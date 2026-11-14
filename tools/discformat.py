"""Disc image input formats for the Dreamcast GD-ROM release tools (stdlib only, Python 3.8+).

Shared by tools/release.py (maintainer) and the player-side apply_patch.py, which ships a copy
(patcher/discformat.py).  No game-specific numbers live here; the layout comes from the release
MANIFEST.json (or tools/release.py for the repo's own source disc).

Supported inputs (docs/xdelta-release.md has the full definition):

  cue         Redump style: a .cue naming one raw 2352-byte BINARY file per track (5 for this game).
  gdi         .gdi text (first line = track count, then `track lba ctl 2352 "file" 0`) with raw
              2352-byte track files (track01.bin, track02.raw, track03.bin ...).
  volume-iso  ONE file of 2048-byte sectors in which sector k is LBA hd_base+k (hd_base = 45000):
              the user data of the high-density area, i.e. the ISO9660 volume (IP.BIN in sectors
              0-15, ISO9660 primary volume descriptor at sector 16).  Audio track 4 and the pregap
              of track 5 are zero sectors.  Size = volume space size * 2048.

Everything else is recognised and refused with an explanation (see `explain`).
"""
import hashlib
import os
import re
import zlib

SS = 2352
USER = 2048
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
IP_MAGIC = b"SEGA SEGAKATANA"
PVD_MAGIC = b"\x01CD001\x01"
HD_BASE = 45000
CHUNK = 1 << 24


class DiscError(Exception):
    """A readable problem with an input (printed without a traceback)."""


# ----------------------------------------------------------------------------- hashing
def hash_file(path, progress=None):
    """size, crc32, md5, sha1, sha256 of a file in one pass (hex strings)."""
    crc = 0
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    size = os.path.getsize(path)
    done = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            crc = zlib.crc32(b, crc)
            md5.update(b)
            sha1.update(b)
            sha256.update(b)
            done += len(b)
            if progress:
                progress(done, size)
    return {"size": size, "crc32": "%08x" % (crc & 0xFFFFFFFF), "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}


# ----------------------------------------------------------------------------- cue / gdi
def parse_cue(path):
    """[{'track': n, 'type': 'MODE1/2352'|'AUDIO'|..., 'file': absolute path, 'file_name': as written}]
    in track order.  Only the FILE/TRACK structure is read (INDEX lines are ignored)."""
    base = os.path.dirname(os.path.abspath(path))
    with open(path, "rb") as f:
        text = f.read().decode("utf-8", "replace")
    tracks = []
    cur_file = None
    for line in text.splitlines():
        s = line.strip()
        up = s.upper()
        if up.startswith("FILE "):
            m = re.match(r'FILE\s+(?:"([^"]*)"|(\S+))\s*(\S*)', s, re.I)
            if not m:
                raise DiscError("cannot read this line of %s: %s" % (path, s))
            cur_file = m.group(1) if m.group(1) is not None else m.group(2)
            cur_file_used = False
        elif up.startswith("TRACK "):
            parts = s.split()
            if len(parts) < 3 or cur_file is None:
                raise DiscError("cannot read this line of %s: %s" % (path, s))
            tracks.append({"track": int(parts[1]), "type": parts[2].upper(), "file_name": cur_file,
                           "file": os.path.normpath(os.path.join(base, cur_file.replace("\\", os.sep)))})
    if not tracks:
        raise DiscError("%s has no TRACK lines" % path)
    return tracks


_GDI = re.compile(r'^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:"([^"]*)"|(\S+))\s+(\d+)\s*$')


def parse_gdi(path):
    """[{'track', 'lba', 'ctl', 'secsize', 'file_name', 'file', 'offset'}] in file order."""
    base = os.path.dirname(os.path.abspath(path))
    with open(path, "rb") as f:
        lines = [l.strip() for l in f.read().decode("utf-8", "replace").splitlines() if l.strip()]
    if not lines or not lines[0].isdigit():
        raise DiscError("%s is not a .gdi file (the first line must be the track count)" % path)
    out = []
    for l in lines[1:]:
        m = _GDI.match(l)
        if not m:
            raise DiscError("cannot read this line of %s: %s" % (path, l))
        name = m.group(5) if m.group(5) is not None else m.group(6)
        out.append({"track": int(m.group(1)), "lba": int(m.group(2)), "ctl": int(m.group(3)),
                    "secsize": int(m.group(4)), "file_name": name, "offset": int(m.group(7)),
                    "file": os.path.normpath(os.path.join(base, name.replace("\\", os.sep)))})
    if len(out) != int(lines[0]):
        raise DiscError("%s says %s tracks but lists %d" % (path, lines[0], len(out)))
    return out


# ----------------------------------------------------------------------------- sniffing
def _read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def sniff(path):
    """(kind, note) for any input file.  kind is one of
    cue, gdi, volume-iso, full-iso, iso-no-ip, raw-track3, raw-track, track-iso, unknown."""
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(512)
        if ext == ".cue":
            return "cue", "cue sheet"
        if ext == ".gdi":
            return "gdi", "gdi sheet"
        text = head.decode("latin-1")
        if size < 65536 and all(c in "\r\n\t" or 32 <= ord(c) < 127 for c in text[:200]):
            first = text.split("\n", 1)[0].strip()
            if first.isdigit():
                return "gdi", "gdi sheet"
            if re.search(r"^\s*FILE\s", text, re.I | re.M):
                return "cue", "cue sheet"
        if size % USER == 0 and size >= 17 * USER and _read_at(f, 16 * USER, 7) == PVD_MAGIC:
            if head[:len(IP_MAGIC)] == IP_MAGIC:
                return "volume-iso", "%d sectors of 2048 bytes" % (size // USER)
            return "iso-no-ip", "an ISO9660 image without a Dreamcast IP.BIN"
        if size >= (HD_BASE + 17) * USER and size % USER == 0 and _read_at(f, (HD_BASE + 16) * USER, 7) == PVD_MAGIC:
            return "full-iso", "cooked image addressed from LBA 0"
        if size % SS == 0 and head[:12] == SYNC:
            if size >= 17 * SS and _read_at(f, 16 * SS + 16, 7) == PVD_MAGIC:
                if _read_at(f, 16, len(IP_MAGIC)) == IP_MAGIC:
                    return "raw-track3", "raw 2352-byte data track starting at LBA 45000"
                return "raw-track", "raw 2352-byte data track with an ISO9660 volume"
            return "raw-track", "raw 2352-byte data track"
        if size % USER == 0 and head[:len(IP_MAGIC)] == IP_MAGIC:
            return "track-iso", "2048-byte data track (IP.BIN first)"
    return "unknown", "not a recognised disc image"


def explain(kind, path):
    base = os.path.basename(path)
    msgs = {
        "full-iso": "%s is a 2048-byte image that starts at LBA 0 (ISO9660 volume descriptor at sector %d). "
                    "Only the high-density 'volume ISO' (sector 0 = LBA %d, descriptor at sector 16) is supported; "
                    "use the .cue/.gdi with the raw tracks instead." % (base, HD_BASE + 16, HD_BASE),
        "iso-no-ip": "%s is an ordinary ISO9660 image without the Dreamcast IP.BIN in sector 0, not a GD-ROM data image."
                     % base,
        "raw-track3": "%s is a single raw track file. Give apply_patch.py the .cue or .gdi that lists all the tracks." % base,
        "raw-track": "%s is a single raw track file. Give apply_patch.py the .cue or .gdi that lists all the tracks." % base,
        "track-iso": "%s looks like a single 2048-byte data track (e.g. track03.iso). Per-track cooked files are not "
                     "supported: use the raw .cue/.gdi set or one 'volume ISO'." % base,
        "unknown": "%s is not a .cue, .gdi or Dreamcast volume .iso that this patch knows." % base,
    }
    return msgs.get(kind, "%s: unsupported input (%s)" % (base, kind))


class Disc:
    """A resolved input.  kind 'cue'/'gdi': tracks {n: path}, sheet = the .cue/.gdi path; 'iso': iso = path."""

    def __init__(self, kind, path):
        self.kind = kind
        self.path = os.path.abspath(path)
        self.tracks = {}
        self.sheet = None
        self.iso = None
        self.entries = []


def open_disc(path, ntracks=5):
    """Detect the format of `path` and map its tracks to files; raises DiscError with a clear message."""
    if not os.path.isfile(path):
        raise DiscError("no such file: %s" % path)
    kind, _ = sniff(path)
    if kind == "volume-iso":
        d = Disc("iso", path)
        d.iso = d.path
        return d
    if kind not in ("cue", "gdi"):
        raise DiscError(explain(kind, path))
    d = Disc(kind, path)
    d.sheet = d.path
    if kind == "cue":
        ents = parse_cue(path)
        files = [e["file"] for e in ents]
        if len(set(files)) != len(files):
            raise DiscError("%s puts several tracks in one file; only a cue with one file per track is supported" % path)
        nums = [e["track"] for e in ents]
    else:
        ents = parse_gdi(path)
        bad = [e for e in ents if e["secsize"] != SS or e["offset"] != 0]
        if bad:
            raise DiscError("%s: track %d uses %d-byte sectors (offset %d); only raw 2352-byte track files are "
                            "supported in a .gdi" % (path, bad[0]["track"], bad[0]["secsize"], bad[0]["offset"]))
        nums = [e["track"] for e in ents]
    if sorted(nums) != list(range(1, ntracks + 1)):
        raise DiscError("%s lists tracks %s; this game's disc has tracks 1-%d" % (path, nums, ntracks))
    for e in ents:
        if not os.path.isfile(e["file"]):
            raise DiscError("%s names a track file that does not exist: %s" % (path, e["file"]))
        d.tracks[e["track"]] = e["file"]
    d.entries = ents
    return d
