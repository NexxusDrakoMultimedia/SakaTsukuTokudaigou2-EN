"""Raw Mode 1 2352-byte tracks -> the 'volume ISO' (cooked 2048-byte sectors), stdlib only.

Maintainer side of the release tooling (tools/release.py); players never need it.  The reverse
(cooked -> raw) is not needed.

Volume ISO of a Dreamcast GD-ROM (docs/xdelta-release.md): file sector k is disc LBA hd_base + k, for
k = 0 .. end - hd_base.  Data tracks (3 and 5) contribute the 2048 user bytes of each sector; the audio
track between them and any other space contribute zero sectors.  A raw sector that is all zero (the
unused start of track 5's pregap) cooks to 2048 zero bytes; a sector with sync but a mode other than 1,
or non-zero junk without sync, is an error rather than silently exported.
"""
import os

from discformat import SS, USER, SYNC, DiscError

SECTORS_PER_CHUNK = 4096


def cook(raw, first_lba=0):
    """2048-byte user data for each raw sector in `raw` (length a multiple of 2352)."""
    if len(raw) % SS:
        raise DiscError("raw data is not a whole number of 2352-byte sectors")
    n = len(raw) // SS
    out = bytearray(n * USER)
    zero = bytes(SS)
    mv = memoryview(raw)
    for i in range(n):
        s = mv[i * SS:(i + 1) * SS]
        if s[:12] == SYNC:
            if s[15] != 1:
                raise DiscError("sector at LBA %d is mode %d, only Mode 1 data is supported" % (first_lba + i, s[15]))
            out[i * USER:(i + 1) * USER] = s[16:16 + USER]
        elif s != zero:
            raise DiscError("sector at LBA %d has no sync pattern and is not all zero" % (first_lba + i))
    return bytes(out)


def export_volume_iso(tracks, out_path, hd_base=45000, progress=None):
    """tracks: [(lba_of_file_start, kind 'data'|'audio', path)] for the high-density area (lba >= hd_base).
    Writes out_path and returns the number of 2048-byte sectors written."""
    segs = sorted(t for t in tracks if t[0] >= hd_base)
    if not segs:
        raise DiscError("no high-density tracks to export")
    pos = hd_base
    zeros = bytes(USER * SECTORS_PER_CHUNK)
    tmp = out_path + ".partial"
    try:
        with open(tmp, "wb") as fo:
            for lba, kind, path in segs:
                n = os.path.getsize(path) // SS
                if os.path.getsize(path) % SS:
                    raise DiscError("%s is not a whole number of 2352-byte sectors" % path)
                if lba < pos:
                    raise DiscError("track at LBA %d overlaps the previous one (ends %d)" % (lba, pos))
                gap = lba - pos
                while gap:
                    k = min(gap, SECTORS_PER_CHUNK)
                    fo.write(zeros[:k * USER])
                    gap -= k
                if kind == "data":
                    with open(path, "rb") as fi:
                        done = 0
                        while done < n:
                            k = min(SECTORS_PER_CHUNK, n - done)
                            fo.write(cook(fi.read(k * SS), lba + done))
                            done += k
                else:
                    left = n
                    while left:
                        k = min(left, SECTORS_PER_CHUNK)
                        fo.write(zeros[:k * USER])
                        left -= k
                pos = lba + n
                if progress:
                    progress(pos - hd_base)
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return pos - hd_base
