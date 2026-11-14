# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure xdelta patch sizes of a built disc against the original (positional vs move-aware encoder).

    python -I -X utf8 tools/re/rel_measure.py <built .gdi or .cue> [--work build/rel_work_measure] [--no-raw]

Exports the built disc to a volume ISO (once, cached in --work), then makes the ISO patch and the raw
track 3 / track 5 patches both ways, re-applies each with vcdiff.py and compares the hash.
Writes only into --work (the caller deletes it).
"""
import argparse
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import discformat as DF   # noqa: E402
import discbuild          # noqa: E402
import isoexport          # noqa: E402
import vcdiff             # noqa: E402


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def make(label, src, tgt, move, work):
    out = os.path.join(work, "m.xdelta")
    t0 = time.time()
    with open(src, "rb") as fs, open(tgt, "rb") as ft, open(out, "wb") as fo:
        vcdiff.encode(fs, ft, fo, hashes=False, move=move)
    t1 = time.time() - t0
    size = os.path.getsize(out)
    stats = dict(vcdiff.LAST_STATS)
    t0 = time.time()
    chk = os.path.join(work, "chk.tmp")
    with open(out, "rb") as f:
        patch = f.read()
    with open(src, "rb") as fs, open(chk, "w+b") as fo:
        vcdiff.decode(fs, patch, fo)
    ok = os.path.getsize(chk) == os.path.getsize(tgt) and sha1(chk) == sha1(tgt)
    os.remove(chk)
    print("  %-34s %12s bytes  make %5.1f s  apply %5.1f s  %s  %s" % (
        label, "{:,}".format(size), t1, time.time() - t0, "OK" if ok else "MISMATCH", stats), flush=True)
    return size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("disc")
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "rel_work_measure"))
    ap.add_argument("--no-raw", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    d = DF.open_disc(a.disc)
    src = {n: os.path.join(ROOT, discbuild.BASE % n) for n in range(1, 6)}
    iso_s = os.path.join(a.work, "source.iso")
    iso_t = os.path.join(a.work, "built.iso")
    hd = [(discbuild.TRACK_LBA[n], "data" if n in discbuild.DATA_TRACKS else "audio") for n in (3, 4, 5)]
    t0 = time.time()
    if not os.path.exists(iso_s):
        isoexport.export_volume_iso([(hd[i][0], hd[i][1], src[3 + i]) for i in range(3)], iso_s, 45000)
    isoexport.export_volume_iso([(hd[i][0], hd[i][1], d.tracks[3 + i]) for i in range(3)], iso_t, 45000)
    print("exported in %.1f s" % (time.time() - t0))
    print("volume ISO %s -> %s" % ("{:,}".format(os.path.getsize(iso_s)), "{:,}".format(os.path.getsize(iso_t))))
    make("ISO positional", iso_s, iso_t, None, a.work)
    make("ISO move-aware", iso_s, iso_t, (2048, 0, 2048), a.work)
    if not a.no_raw:
        for n in (3, 5):
            if os.path.getsize(src[n]) and sha1(src[n]) == sha1(d.tracks[n]):
                print("  track %d unchanged" % n)
                continue
            make("track %d positional" % n, src[n], d.tracks[n], None, a.work)
            make("track %d move-aware" % n, src[n], d.tracks[n], (2352, 16, 2048), a.work)


if __name__ == "__main__":
    main()
