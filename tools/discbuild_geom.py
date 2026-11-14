"""Disc geometry model of a Dreamcast GD-ROM dump (Redump bin/cue + gdi).  Pure stdlib, no dependency on discbuild.

A GD-ROM image = tracks 1-2 (low-density area, LBA 0..) and tracks 3..N (high-density area, LBA 45000..549149).
Each track file holds 2352-byte raw sectors, INCLUDING its pregap, so a track's 'lba' is the LBA of the first sector of its
FILE (not of INDEX 01), exactly as the .gdi lists it.  The ISO9660 volume lives in the high-density data tracks.

    g = Geometry.default()                      # this game's original layout
    g = Geometry.from_gdi(path_to_gdi)          # any dump (sizes read from the track files next to it)
    g = Geometry.from_cue(path_to_cue)          # same, from the cue sheet (also gives the pregaps)
    g.gdi_text(name) / g.cue_text(name)         # the sheets for the geometry (default geometry == discbuild's output)
    g.hd_regions()                              # [(first, end)] LBA ranges that may hold ISO9660 extents

See docs/disc-layout.md (PROVEN track facts) and docs/expansion/disc-layout.md s2/s5.
"""
import os
import re

SS = 2352
HD_BASE = 45000
HD_END = 549150            # first LBA after the last sector a GD-ROM high-density area can hold (spec ceiling)


class GeometryError(Exception):
    pass


class Track:
    __slots__ = ("no", "kind", "lba", "nsec", "pregap", "file")

    def __init__(self, no, kind, lba, nsec, pregap=0, file=None):
        self.no, self.kind, self.lba, self.nsec, self.pregap, self.file = no, kind, lba, nsec, pregap, file

    @property
    def data(self):
        return self.kind == "data"

    @property
    def ctl(self):
        return 4 if self.data else 0

    @property
    def end(self):
        """First LBA after the last sector of the track file."""
        return self.lba + self.nsec

    @property
    def first(self):
        """First LBA of INDEX 01 (after the pregap held in the file)."""
        return self.lba + self.pregap

    def __repr__(self):
        return "Track(%d %s lba=%d n=%d pre=%d)" % (self.no, self.kind, self.lba, self.nsec, self.pregap)


# this game: (no, kind, file start LBA, file sectors, pregap sectors inside the file)
_DEFAULT = ((1, "data", 0, 2380, 0), (2, "audio", 2380, 888, 150), (3, "data", 45000, 6342, 0),
            (4, "audio", 51342, 5323, 150), (5, "data", 56665, 492485, 225))


class Geometry:
    def __init__(self, tracks, hd_base=HD_BASE, max_lba=HD_END):
        self.tracks = {t.no: t for t in tracks}
        self.order = sorted(self.tracks)
        self.hd_base = hd_base
        self.max_lba = max_lba

    # ---- constructors
    @classmethod
    def default(cls, track5_sectors=None):
        ts = [Track(n, k, l, s, p) for n, k, l, s, p in _DEFAULT]
        g = cls(ts)
        if track5_sectors is not None:
            g.tracks[5].nsec = track5_sectors
        return g

    @classmethod
    def from_gdi(cls, gdi_path, pregaps=None):
        """Parse a .gdi.  Sector counts come from the size of the track files beside it.  `pregaps` {track: sectors}
        (a gdi does not carry them; the default geometry's are used when omitted)."""
        base = os.path.dirname(os.path.abspath(gdi_path))
        with open(gdi_path, encoding="utf8", newline="") as f:
            lines = [l.strip() for l in f.read().splitlines() if l.strip()]
        try:
            n = int(lines[0])
        except (ValueError, IndexError):
            raise GeometryError("gdi: first line must be the track count")
        pg = {no: p for no, _k, _l, _s, p in _DEFAULT}
        pg.update(pregaps or {})
        ts = []
        for ln in lines[1:]:
            m = re.match(r'^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:"([^"]+)"|(\S+))\s+(\d+)$', ln)
            if not m:
                raise GeometryError("gdi: cannot parse line %r" % ln)
            no, lba, typ, ssz = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            fn = m.group(5) or m.group(6)
            if ssz != SS:
                raise GeometryError("gdi: track %d sector size %d, expected 2352" % (no, ssz))
            p = os.path.join(base, fn)
            nsec = os.path.getsize(p) // SS if os.path.exists(p) else 0
            ts.append(Track(no, "data" if typ == 4 else "audio", lba, nsec, pg.get(no, 0) if no > 1 else 0, fn))
        if len(ts) != n:
            raise GeometryError("gdi: header says %d tracks, found %d" % (n, len(ts)))
        return cls(ts)

    @classmethod
    def from_cue(cls, cue_path, hd_base=HD_BASE):
        """Parse a cue sheet like the Redump one: FILE / TRACK / INDEX 00,01; 'REM HIGH-DENSITY AREA' restarts the LBA
        at hd_base.  Sector counts come from the track files beside the cue."""
        base = os.path.dirname(os.path.abspath(cue_path))
        with open(cue_path, encoding="utf8", newline="") as f:
            lines = f.read().splitlines()
        ts, cur, hd_seen = [], None, False
        for ln in lines:
            s = ln.strip()
            if s.upper().startswith("REM HIGH-DENSITY"):
                hd_seen = True
            m = re.match(r'^FILE\s+"([^"]+)"\s+BINARY$', s, re.I)
            if m:
                cur = {"file": m.group(1), "idx": {}, "hd": hd_seen}
                continue
            m = re.match(r"^TRACK\s+(\d+)\s+(\S+)$", s, re.I)
            if m and cur is not None:
                cur["no"] = int(m.group(1))
                mode = m.group(2).upper()
                if mode not in ("MODE1/2352", "AUDIO"):
                    raise GeometryError("cue: track %s mode %s unsupported" % (m.group(1), mode))
                cur["kind"] = "audio" if mode == "AUDIO" else "data"
                ts.append(cur)
                continue
            m = re.match(r"^INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)$", s, re.I)
            if m and cur is not None:
                cur["idx"][int(m.group(1))] = (int(m.group(2)) * 60 + int(m.group(3))) * 75 + int(m.group(4))
        out, lba, in_hd = [], 0, False
        for c in ts:
            if c["hd"] and not in_hd:
                lba, in_hd = hd_base, True
            p = os.path.join(base, c["file"])
            nsec = os.path.getsize(p) // SS if os.path.exists(p) else 0
            if 1 not in c["idx"]:
                raise GeometryError("cue: track %d has no INDEX 01" % c["no"])
            pre = c["idx"][1] - c["idx"].get(0, 0)
            out.append(Track(c["no"], c["kind"], lba, nsec, pre, c["file"]))
            lba += nsec
        return cls(out)

    # ---- queries
    @property
    def end_lba(self):
        t = self.tracks[self.order[-1]]
        return t.end

    def track_at(self, lba):
        for n in self.order:
            t = self.tracks[n]
            if t.lba <= lba < t.end:
                return t
        return None

    def hd_data_tracks(self):
        return [self.tracks[n] for n in self.order if self.tracks[n].data and self.tracks[n].lba >= self.hd_base]

    def hd_regions(self):
        """[(first, end)] LBA ranges (INDEX 01 onward, pregap excluded) of the high-density data tracks."""
        return [(t.first, t.end) for t in self.hd_data_tracks()]

    def in_hd_data(self, lba, nsec=1):
        """True if [lba, lba+nsec) lies wholly inside ONE high-density data track (after its pregap)."""
        return any(a <= lba and lba + nsec <= b for a, b in self.hd_regions())

    def with_track5_sectors(self, n):
        g = Geometry([Track(t.no, t.kind, t.lba, t.nsec, t.pregap, t.file) for t in self.tracks.values()],
                     self.hd_base, self.max_lba)
        g.tracks[self.order[-1]].nsec = n
        return g

    def check(self):
        """Problems with the geometry itself ([] if sound): contiguous areas, hd start, ceiling."""
        bad = []
        prev = None
        for n in self.order:
            t = self.tracks[n]
            if prev is not None and t.lba != prev.end and not (prev.end <= self.hd_base == t.lba):
                bad.append("track %d starts at %d but track %d ends at %d" % (t.no, t.lba, prev.no, prev.end))
            if t.nsec <= 0:
                bad.append("track %d has no sectors" % t.no)
            if t.pregap > t.nsec:
                bad.append("track %d pregap %d > size" % (t.no, t.pregap))
            prev = t
        hd = [self.tracks[n] for n in self.order if self.tracks[n].lba >= self.hd_base]
        if hd and hd[0].lba != self.hd_base:
            bad.append("first high-density track starts at %d, expected %d" % (hd[0].lba, self.hd_base))
        if self.end_lba > self.max_lba:
            bad.append("disc ends at LBA %d, past the GD-ROM ceiling %d (%d sectors over)" % (
                self.end_lba, self.max_lba, self.end_lba - self.max_lba))
        return bad

    # ---- sheets (byte-identical to the Redump sheets of this game for the default geometry)
    def gdi_text(self, name):
        lines = [str(len(self.order))]
        for n in self.order:
            t = self.tracks[n]
            lines.append('%d %d %d 2352 "%s (Track %d).bin" 0' % (t.no, t.lba, t.ctl, name, t.no))
        return "\r\n".join(lines) + "\r\n"

    def cue_text(self, name):
        out = []
        hd_marked = False
        for n in self.order:
            t = self.tracks[n]
            if n == self.order[0]:
                out.append("REM SINGLE-DENSITY AREA\r\n")
            if t.lba >= self.hd_base and not hd_marked:
                out.append("REM HIGH-DENSITY AREA\r\n")
                hd_marked = True
            out.append('FILE "%s (Track %d).bin" BINARY\r\n' % (name, t.no))
            out.append("  TRACK %02d %s\r\n" % (t.no, "MODE1/2352" if t.data else "AUDIO"))
            if t.pregap:
                out.append("    INDEX 00 00:00:00\r\n")
                f = t.pregap
                out.append("    INDEX 01 %02d:%02d:%02d\r\n" % (f // 4500, f % 4500 // 75, f % 75))
            else:
                out.append("    INDEX 01 00:00:00\r\n")
        return "".join(out)

    def describe(self):
        return ", ".join("T%d %s %d..%d" % (t.no, t.kind[0], t.lba, t.end) for t in (self.tracks[n] for n in self.order))
