# SPDX-License-Identifier: GPL-3.0-or-later
"""Checks tools/bincue2iso.py on the repo's own Redump dump: volume ISO size/PVD, every file of the disc compared
byte-for-byte with the raw tracks (read through tools/gdrom.py), per-track output sizes, GDI input, refusal to
overwrite.  Writes only under build/iso_test/.   python -I -X utf8 tools/test_bincue2iso.py"""
import os, sys, shutil, struct, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gdrom, bincue2iso as B

CUE = os.path.join(ROOT, "Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan).cue")
OUT = os.path.join(ROOT, "build", "iso_test")
fails = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
iso = os.path.join(OUT, "volume.iso")
tracks = B.load_tracks(CUE)
check([t.lba for t in tracks] == [0, 2380, 45000, 51342, 56665], "cue: track LBAs follow the GD-ROM layout")
sectors, st = B.write_volume(tracks, iso, True)
check(sectors == 504150 and os.path.getsize(iso) == 504150 * 2048, "volume: 504150 sectors x 2048")
check(st.bad_sync == 0 and st.bad_msf == 0 and st.bad_mode == 0, "volume: every sector has sync, MSF=LBA+150, mode 1")

import tomllib
with open(os.path.join(HERE, "release.toml"), "rb") as _f:
    _want = tomllib.load(_f)["source"]["volume_iso"]
_h = hashlib.sha1()
with open(iso, "rb") as _f:
    for _b in iter(lambda: _f.read(1 << 24), b""):
        _h.update(_b)
check(_h.hexdigest() == _want["sha1"], "volume: SHA-1 equals the volume ISO hash recorded in tools/release.toml (== tools/isoexport.py)")

with open(iso, "rb") as f:
    f.seek(16 * 2048)
    pvd = f.read(2048)
    check(pvd[0] == 1 and pvd[1:6] == b"CD001", "volume: PVD at sector 16")
    vss, = struct.unpack_from("<I", pvd, 80)
    check(vss == 504150, "volume: PVD volume space size equals the ISO length")
    f.seek(0)
    sysarea = f.read(16 * 2048)
    check(sysarea[:15] == b"SEGA SEGAKATANA", "volume: IP.BIN in the system area")

disc = gdrom.Disc(ROOT)
r = gdrom.pvd_root(disc)
files = list(gdrom.walk(disc, *r))
check(len(files) == 1215, "disc: 1215 files found through the raw tracks")
bad = 0
with open(iso, "rb") as f:
    for p, lba, size in files:
        f.seek((lba - 45000) * 2048)
        a = f.read(size)
        b = disc.read(lba, size)
        if a != b:
            bad += 1
            print("   differs:", p)
check(bad == 0, "volume: all %d files identical to the raw tracks" % len(files))

d2 = os.path.join(OUT, "tracks")
os.makedirs(d2)
res = B.write_tracks(tracks, d2, True)
sizes = {t.num: os.path.getsize(p) for t, p, s in res}
check(sizes == {1: 2380 * 2048, 3: 6342 * 2048, 5: 492485 * 2048}, "tracks: data tracks 1, 3, 5 cooked, audio skipped")

# GDI input: write a .gdi next to copies is expensive (1.1 GB), so use a gdi that points at the repo's bins by name
gdi = os.path.join(ROOT, "build", "iso_test", "x.gdi")
lines = ["5"]
for t, (lba, ctrl) in zip(tracks, [(0, 4), (2380, 0), (45000, 4), (51342, 0), (56665, 4)]):
    lines.append('%d %d %d 2352 "%s" 0' % (t.num, lba, ctrl, os.path.relpath(t.path, os.path.dirname(gdi)).replace("\\", "/")))
open(gdi, "w", newline="\n").write("\n".join(lines) + "\n")
gt = B.load_tracks(gdi)
check([(t.kind, t.lba) for t in gt] == [("data", 0), ("audio", 2380), ("data", 45000), ("audio", 51342), ("data", 56665)],
      "gdi: parsed like the cue")
iso2 = os.path.join(OUT, "volume2.iso")
B.write_volume(gt, iso2, False)


def sha(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


check(sha(iso) == sha(iso2), "gdi input gives the identical volume ISO")

# CLI refuses to overwrite an existing output and an input
rc = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "bincue2iso.py"), CUE, iso],
                    capture_output=True, text=True)
check(rc.returncode == 1 and "exists" in rc.stderr, "cli: refuses to overwrite an existing output without --force")
rc = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "bincue2iso.py"), CUE, tracks[2].path, "--force"],
                    capture_output=True, text=True)
check(rc.returncode == 1 and "overwrite an input" in rc.stderr, "cli: refuses to overwrite an input track")

print("RESULT: %d failed" % len(fails) if fails else "RESULT: all passed")
sys.exit(1 if fails else 0)
