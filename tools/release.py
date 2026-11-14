# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Build a SakaTsuku2-EN release: xdelta (VCDIFF) patches against the player's own dump, checked and hashed.

Modelled on LMASTER-Mod's tools/build_release.py (same author, GPL-3.0-or-later). Python 3.11+ (tomllib).

    python -I -X utf8 tools/release.py [SOURCE] --date YYYY-MM-DD [--version V] [--out dist] [--work build/release]
                                       [build_patch.py options, e.g. --proportional-font on --repack off; none = the standard flags of release.toml:
                                        --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict]

SOURCE is the disc the patches are made against: a .cue, .gdi or volume .iso (default: the Redump-style cue in
the repo root). Its tracks are hashed and compared with the hashes recorded in tools/release.toml (clear
message per file when they differ). Then:

  1. tools/build_patch.py builds the patched disc from translation/*.jsonl into <work>/disc (unknown options of
     this program are passed through to it);
  2. every track whose bytes changed (here 3 and 5) and the volume ISO (the patched disc exported to
     2048-byte sectors, tools/isoexport.py) get one VCDIFF patch (tools/vcdiff.py);
  3. each patch is applied again with our decoder AND with xdelta3 (if found) and the result hashes (size,
     SHA-1, SHA-256) are compared with the built files;
  4. dist/<project>-<version>/ gets the .xdelta files (raw track 3 / 5 patches for BIN/CUE and GDI, volume-ISO patch;
     the encoder is move-aware, so relocated files stay small), MANIFEST.json (v2: also how raw tracks are rebuilt from
     the patched ISO), HASHES.txt, SHA256SUMS, README.md, TRANSLATORS_NOTES.md (from [bundle] in tools/release.toml; the
     bundle FAILS while it still contains the word PLACEHOLDER, unless --allow-placeholder), apply_patch.py (ONE
     stdlib-only file, the decoder and disc code embedded), verify_dist.py, LICENSE, NOTICE.txt, VERSION; plus
     dist/<project>-<version>.zip and .zip.sha256.

--built-disc DISC uses an existing trial disc as the patched side (no build_patch.py run; the bundle is marked as a
development build). --print-dev-toml DISC prints its [dev.NAME] hash table for release.toml.

The build date is the --date argument (never read from the clock). Nothing under extracted/, translation/ or the
original tracks is written. --reuse-build skips step 1 when <work>/disc already holds a build.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import discformat as DF      # noqa: E402
import isoexport             # noqa: E402
import bincue2iso as BC      # noqa: E402
import vcdiff                # noqa: E402
import discbuild             # noqa: E402

PROJECT = "SakaTsuku2-EN"
TITLE = "Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan)"
GDI_NAMES = {1: "track01.bin", 2: "track02.raw", 3: "track03.bin", 4: "track04.raw", 5: "track05.bin"}
# The official regular expression of SemVer 2.0.0 (semver.org; named groups turned into numbered ones, so group 4 is the
# prerelease and group 5 the build metadata, used below): numeric identifiers have no leading zero, no identifier is empty.
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
                    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\Z")
# An absolute home-directory path of the maintainer's machine (Windows, MSYS/Git-Bash, Linux, macOS style).
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+|/(?:mnt/)?[a-z]/Users/[^/\s]+|/home/[^/\s]+|/Users/[^/\s]+)", re.I)


def scrub_paths(text):
    """Remove absolute local paths from text that goes into a bundle: the repo root becomes a repo-relative path, the running
    interpreter becomes 'python', any other home-directory path becomes '<home>'."""
    def variants(p):
        p = os.path.abspath(p)
        return sorted({p, p.replace("\\", "/"), p.replace("/", "\\")}, key=len, reverse=True)
    for exe in {sys.executable, os.path.realpath(sys.executable)}:
        for v in variants(exe):
            text = re.sub(re.escape(v), "python", text, flags=re.I)
    for v in variants(ROOT):
        text = re.sub(re.escape(v) + r"[\\/]?", "", text, flags=re.I)
    return LOCAL_PATH_RE.sub("<home>", text)


def local_paths_in(folder):
    """Files of a bundle folder that contain an absolute local home-directory path (relative names, sorted)."""
    bad = []
    for top, _, files in os.walk(folder):
        for n in files:
            with open(os.path.join(top, n), "rb") as f:
                data = f.read()
            if LOCAL_PATH_RE.search(data.decode("utf-8", errors="replace")):
                bad.append(os.path.relpath(os.path.join(top, n), folder).replace(os.sep, "/"))
    return sorted(bad)
XDELTA3_FALLBACK = r"C:\ProgramData\chocolatey\bin\xdelta3.exe"
HASH_KEYS = ("size", "crc32", "md5", "sha1", "sha256")


def fail(msg):
    raise SystemExit("error: " + msg)


def log(*a):
    print(*a, flush=True)


def human(n):
    return "{:,}".format(n)


def game_layout():
    """The disc geometry of this game (from tools/discbuild.py) in the form MANIFEST.json records."""
    tracks = {}
    for n in range(1, 6):
        tracks[n] = {"kind": "data" if n in discbuild.DATA_TRACKS else "audio",
                     "lba": discbuild.TRACK_LBA[n],
                     "redump_name": "%s (Track %d).bin" % (TITLE, n),
                     "gdi_name": GDI_NAMES[n]}
    return {"title": TITLE, "hd_base": discbuild.HD_BASE, "tracks": tracks}


def repo_source_tracks():
    return {n: os.path.join(ROOT, discbuild.BASE % n) for n in range(1, 6)}


def find_xdelta3():
    import shutil as _sh
    exe = _sh.which("xdelta3")
    if not exe and os.path.exists(XDELTA3_FALLBACK):
        exe = XDELTA3_FALLBACK
    return exe


# ----------------------------------------------------------------------------- config
def load_config(path=None):
    import tomllib
    with open(path or os.path.join(HERE, "release.toml"), "rb") as f:
        return tomllib.load(f)


def read_version(path=None):
    with open(path or os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
        v = f.read().strip()
    if not SEMVER.match(v):
        fail("VERSION %r is not a semantic version (semver.org)" % v)
    return v


def recorded(cfg, key):
    """The hash dict recorded in release.toml for 'track1'..'track5' or 'volume_iso'."""
    src = cfg.get("source", {})
    h = src.get(key)
    if not h or not all(k in h for k in HASH_KEYS):
        fail("tools/release.toml has no recorded hashes for %s; run with --print-source-toml and paste them in" % key)
    return {k: h[k] for k in HASH_KEYS}


def fmt_hash(label, h):
    return "  %-10s %s bytes, CRC-32 %s, MD5 %s, SHA-1 %s, SHA-256 %s" % (
        label, human(h["size"]), h["crc32"], h["md5"], h["sha1"], h["sha256"])


def compare(label, path, got, want):
    """None if equal, else a readable mismatch message."""
    if all(got[k] == want[k] for k in HASH_KEYS):
        return None
    bits = []
    if got["size"] != want["size"]:
        bits.append("size %s, expected %s" % (human(got["size"]), human(want["size"])))
    for k in ("sha1", "sha256", "md5", "crc32"):
        if got[k] != want[k]:
            bits.append("%s %s, expected %s" % (k.upper(), got[k], want[k]))
    return "%s (%s): %s" % (label, path, "; ".join(bits))


# ----------------------------------------------------------------------------- source
def verify_source(path, cfg, layout):
    """Hash the tracks (or the ISO) of the disc at `path` against release.toml. Returns
    (disc, hashes{n or 'iso': hashdict}); exits with a clear message on any mismatch."""
    try:
        disc = DF.open_disc(path, len(layout["tracks"]))
    except DF.DiscError as e:
        fail(str(e))
    problems, hashes = [], {}
    if disc.kind == "iso":
        log("Hashing the source volume ISO %s" % disc.iso)
        h = DF.hash_file(disc.iso)
        hashes["iso"] = h
        m = compare("volume ISO", disc.iso, h, recorded(cfg, "volume_iso"))
        if m:
            problems.append(m)
    else:
        for n in sorted(disc.tracks):
            log("Hashing source track %d: %s" % (n, os.path.basename(disc.tracks[n])))
            h = DF.hash_file(disc.tracks[n])
            hashes[n] = h
            m = compare("track %d" % n, disc.tracks[n], h, recorded(cfg, "track%d" % n))
            if m:
                problems.append(m)
    if problems:
        fail("the source disc %s is not the dump the patches are built against:\n  %s"
             % (path, "\n  ".join(problems)))
    return disc, hashes


# ----------------------------------------------------------------------------- build
BUILD_RE = {
    "records": re.compile(r"translation DB: (\d+) records, (\d+) with English"),
    "digest": re.compile(r"patch digest ([0-9a-f]{40})"),
    "files": re.compile(r"files changed: (\d+)"),
    "disc": re.compile(r"disc: (\d+) sectors rewritten, (\d+) file\(s\) moved, end LBA (\d+) -> (\d+)"),
}


def run_build(work, bp_args, reuse):
    disc_dir = os.path.join(work, "disc")
    name = PROJECT
    tracks = {n: discbuild.track_path(disc_dir, name, n) for n in range(1, 6)}
    logp = os.path.join(work, "build.log")
    if reuse and all(os.path.exists(p) for p in tracks.values()) and os.path.exists(logp):
        log("Reusing the build in %s" % disc_dir)
        with open(logp, encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        os.makedirs(work, exist_ok=True)
        shutil.rmtree(disc_dir, ignore_errors=True)
        cmd = [sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "build_patch.py"),
               "--out", disc_dir, "--name", name] + bp_args
        log("$ " + " ".join(cmd))
        t0 = time.time()
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        text = p.stdout + p.stderr
        with open(logp, "w", encoding="utf-8", newline="\n") as f:
            f.write("$ " + " ".join(cmd) + "\n" + text)
        if p.returncode not in (0,):
            print(text[-3000:])
            fail("build_patch.py exited with %d (log: %s)" % (p.returncode, logp))
        log("  built in %.0f s" % (time.time() - t0))
    info = {}
    for k, rx in BUILD_RE.items():
        m = rx.search(text)
        info[k] = m.groups() if m else None
    return tracks, info, text


# ----------------------------------------------------------------------------- patches
def run_xdelta3(exe, src, patch, out):
    p = subprocess.run([exe, "-d", "-f", "-s", src, patch, out], capture_output=True, text=True, errors="replace")
    if p.returncode:
        fail("xdelta3 could not apply %s: %s" % (patch, (p.stdout + p.stderr).strip()[-400:]))


MOVE_RAW = (BC.SS, 16, BC.USER)        # raw Mode 1 sector: 2048 user bytes at offset 16
MOVE_ISO = (BC.USER, 0, BC.USER)        # cooked volume ISO


def make_and_check(label, src_path, tgt_path, patch_path, want, work, x3, move=None):
    """VCDIFF src->tgt (move-aware when `move` is given), re-apply with vcdiff.py and xdelta3, compare with `want`
    (hash dict of tgt). Returns the manifest 'patch' entry."""
    t0 = time.time()
    with open(src_path, "rb") as fs, open(tgt_path, "rb") as ft, open(patch_path, "wb") as fo:
        vcdiff.encode(fs, ft, fo, hashes=False, move=move)
    t_make = time.time() - t0
    size = os.path.getsize(patch_path)
    mv = dict(vcdiff.LAST_STATS)
    log("  %s: patch %s bytes (made in %.1f s; %d sectors in %d moved runs, %d windows)" % (
        label, human(size), t_make, mv.get("move_sectors", 0), mv.get("move_regions", 0), mv.get("windows", 0)))
    chk = os.path.join(work, "check.tmp")
    t0 = time.time()
    with open(patch_path, "rb") as f:
        patch = f.read()
    with open(src_path, "rb") as fs, open(chk, "w+b") as fo:
        vcdiff.decode(fs, patch, fo)
    m = compare(label + " (vcdiff.py re-apply)", chk, DF.hash_file(chk), want)
    os.remove(chk)
    if m:
        fail("re-applying the patch did not reproduce the built file: " + m)
    t_apply = time.time() - t0
    log("    re-applied with vcdiff.py in %.1f s: matches the built file" % t_apply)
    x3res = "not run (xdelta3 not found)"
    t_x3 = None
    if x3:
        t0 = time.time()
        run_xdelta3(x3, src_path, patch_path, chk)
        m = compare(label + " (xdelta3 -d)", chk, DF.hash_file(chk), want)
        os.remove(chk)
        if m:
            fail("xdelta3 did not reproduce the built file: " + m)
        t_x3 = time.time() - t0
        x3res = "passed"
        log("    applied with xdelta3 in %.1f s: matches the built file" % t_x3)
    ph = DF.hash_file(patch_path)
    return {"file": os.path.basename(patch_path), "size": ph["size"], "crc32": ph["crc32"], "md5": ph["md5"],
            "sha1": ph["sha1"], "sha256": ph["sha256"],
            "moved_sectors": mv.get("move_sectors", 0), "moved_runs": mv.get("move_regions", 0),
            "checks": {"vcdiff.py": "passed", "xdelta3": x3res},
            "seconds": {"make": round(t_make, 1), "apply_vcdiff_py": round(t_apply, 1),
                        "apply_xdelta3": None if t_x3 is None else round(t_x3, 1)}}


def diff_sector_runs(path_a, path_b, ss=BC.SS, chunk=4096):
    """[(first_sector, count)] of the sectors in which two files of equal size differ."""
    runs = []
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        pos = 0
        while True:
            a, b = fa.read(chunk * ss), fb.read(chunk * ss)
            if not a and not b:
                break
            if a != b:
                for i in range(max(len(a), len(b)) // ss):
                    if a[i * ss:(i + 1) * ss] != b[i * ss:(i + 1) * ss]:
                        k = pos + i
                        if runs and runs[-1][0] + runs[-1][1] == k:
                            runs[-1][1] += 1
                        else:
                            runs.append([k, 1])
            pos += chunk
    return [tuple(r) for r in runs]


def compute_rebuild(src_track, built_iso, built_track, lba, hd_base, work):
    """How apply_patch.py rebuilds this raw track from the patched volume ISO (bincue2iso.rebuild_raw_track): None if
    the built track cannot be reproduced that way, else {"encode": [[first_sector, count], ...], "sectors": N}.
    `encode` lists sector runs that must be written as real Mode 1 sectors although their user bytes equal the
    original's (an all-zero original sector that the disc builder rewrote)."""
    out_sectors = os.path.getsize(built_track) // BC.SS
    tmp = os.path.join(work, "rebuild.tmp")
    try:
        BC.rebuild_raw_track(src_track, built_iso, tmp, lba, hd_base, out_sectors)
        runs = diff_sector_runs(tmp, built_track)
        force = []
        if runs:
            with open(built_track, "rb") as fb, open(built_iso, "rb") as fi:
                for a, n in runs:
                    for k in range(a, a + n):
                        fb.seek(k * BC.SS)
                        raw = fb.read(BC.SS)
                        fi.seek((lba + k - hd_base) * BC.USER)
                        if raw != BC.encode_sector(lba + k, fi.read(BC.USER)):
                            return None
                    force.append([a, n])
            BC.rebuild_raw_track(src_track, built_iso, tmp, lba, hd_base, out_sectors, force)
            if diff_sector_runs(tmp, built_track):
                return None
        return {"encode": force, "sectors": out_sectors}
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def produce(layout, version, date, src_files, src_hashes, built_files, built_hashes, out_dir, work,
            project=PROJECT, extra=None, x3=None, git_commit=None, build_text=None, notes=None, allow_placeholder=False,
            dev_note=None, raw_patches=True, changelog=None, licenses_dir=None):
    """Make patches and the release folder. src_files/built_files: {n: path, 'iso': path};
    *_hashes the matching hash dicts. `notes`: path of the TRANSLATORS_NOTES.md to bundle (None: none).
    `changelog`: path of the CHANGELOG.md to bundle (checked for a `## [version]` section; None: none); `licenses_dir`: the
    LICENSES/ folder to copy into the bundle (None: none).
    raw_patches=False leaves out the raw track patches: BIN/CUE and GDI players then go through the volume-ISO patch
    (apply_patch.py rebuilds the raw tracks), which needs every changed data track to be rebuildable. Returns the
    manifest dict."""
    if notes is not None:
        check_notes(notes, allow_placeholder)
    if changelog is not None:
        check_changelog(changelog, version, strict=not dev_note)
    os.makedirs(out_dir, exist_ok=True)
    man = {"manifest_version": 2, "project": project, "version": version, "build_date": date,
           "git_commit": git_commit, "game": {"title": layout["title"]},
           "layout": {"hd_base": layout["hd_base"],
                      "tracks": {str(n): {"kind": L["kind"], "lba": L["lba"]} for n, L in layout["tracks"].items()}},
           "tracks": {}, "volume_iso": None, "raw_rebuild": {}}
    if dev_note:
        man["dev_build"] = dev_note
    if extra:
        man.update(extra)
    tag = "%s-%s" % (project, version)
    for n in sorted(layout["tracks"]):
        L = layout["tracks"][n]
        e = {"kind": L["kind"], "lba": L["lba"], "redump_name": L["redump_name"], "gdi_name": L["gdi_name"],
             "source": src_hashes[n], "result": built_hashes[n],
             "changed": src_hashes[n]["sha1"] != built_hashes[n]["sha1"] or src_hashes[n]["sha256"] != built_hashes[n]["sha256"]}
        if e["changed"] and raw_patches:
            e["patch"] = make_and_check("track %d" % n, src_files[n], built_files[n],
                                        os.path.join(out_dir, "%s-track%02d.xdelta" % (tag, n)), built_hashes[n], work, x3,
                                        move=MOVE_RAW if L["kind"] == "data" else None)
        man["tracks"][str(n)] = e
    iso = {"source": src_hashes["iso"], "result": built_hashes["iso"],
           "changed": src_hashes["iso"]["sha256"] != built_hashes["iso"]["sha256"]}
    if iso["changed"]:
        iso["patch"] = make_and_check("volume ISO", src_files["iso"], built_files["iso"],
                                      os.path.join(out_dir, "%s-volume-iso.xdelta" % tag), built_hashes["iso"], work, x3,
                                      move=MOVE_ISO)
        for n in sorted(layout["tracks"]):
            L = layout["tracks"][n]
            if man["tracks"][str(n)]["changed"] and L["kind"] == "data" and L["lba"] >= layout["hd_base"]:
                t0 = time.time()
                rb = compute_rebuild(src_files[n], built_files["iso"], built_files[n], L["lba"], layout["hd_base"], work)
                man["raw_rebuild"][str(n)] = rb
                log("  track %d rebuildable from the patched ISO: %s (%.1f s)" % (
                    n, "yes, %d forced run(s)" % len(rb["encode"]) if rb else "NO (apply_patch.py will use the track patch only)",
                    time.time() - t0))
    man["volume_iso"] = iso
    man["raw_patches"] = bool(raw_patches)
    if not raw_patches:
        if not iso["changed"]:
            fail("--no-raw-patches needs a changed volume ISO")
        for n in sorted(layout["tracks"]):
            if man["tracks"][str(n)]["changed"] and not man["raw_rebuild"].get(str(n)):
                fail("--no-raw-patches: track %s cannot be rebuilt from the patched ISO, the raw track patch is needed" % n)
    write_docs(man, out_dir, build_text, notes, allow_placeholder, changelog, licenses_dir)
    return man


# ----------------------------------------------------------------------------- docs
def sizes_line(h):
    return "%s bytes (%.1f MB)" % (human(h["size"]), h["size"] / 1e6)


def write_hashes_txt(man, out_dir):
    L = ["%s %s  (built %s)" % (man["project"], man["version"], man["build_date"]), ""]
    if man.get("git_commit"):
        L += ["git commit %s" % man["git_commit"], ""]
    L += ["The patches apply to YOUR dump of the Japanese disc (%s)." % man["game"]["title"],
          "Hashes below are of the unpatched dump (SOURCE) and of what the patches make (RESULT).", ""]
    for n in sorted(man["tracks"], key=int):
        e = man["tracks"][n]
        L.append("TRACK %s  %s  /  GDI: %s  (%s, LBA %d)%s" % (
            n, e["redump_name"], e["gdi_name"], e["kind"], e["lba"],
            ("  -> PATCHED by %s" % e["patch"]["file"] if e.get("patch") else "  -> PATCHED (via the volume ISO patch)") if e["changed"] else "  -> unchanged, no patch"))
        for k in HASH_KEYS:
            if e["changed"]:
                L.append("    source %-7s %s" % (k, e["source"][k]))
                L.append("    result %-7s %s" % (k, e["result"][k]))
            else:
                L.append("    %-14s %s" % (k, e["source"][k]))
        L.append("")
    v = man["volume_iso"]
    L.append("VOLUME ISO  (one file of 2048-byte sectors, sector 0 = LBA 45000)%s" % (
        "  -> PATCHED by %s" % v["patch"]["file"] if v["changed"] else "  -> unchanged, no patch"))
    for k in HASH_KEYS:
        if v["changed"]:
            L.append("    source %-7s %s" % (k, v["source"][k]))
            L.append("    result %-7s %s" % (k, v["result"][k]))
        else:
            L.append("    %-14s %s" % (k, v["source"][k]))
    L += ["", "PATCH FILES"]
    for n in sorted(man["tracks"], key=int):
        p = man["tracks"][n].get("patch")
        if p:
            L.append("  %s  %s bytes  SHA-1 %s  SHA-256 %s" % (p["file"], human(p["size"]), p["sha1"], p["sha256"]))
    if v.get("patch"):
        p = v["patch"]
        L.append("  %s  %s bytes  SHA-1 %s  SHA-256 %s" % (p["file"], human(p["size"]), p["sha1"], p["sha256"]))
    L += ["", "CHECKS made when this release was built: every patch was applied again with tools/vcdiff.py and with xdelta3",
          "and the output compared (size, SHA-1, SHA-256) with the built file."]
    for n in sorted(man["tracks"], key=int):
        p = man["tracks"][n].get("patch")
        if p:
            L.append("  track %s: vcdiff.py %s, xdelta3 %s" % (n, p["checks"]["vcdiff.py"], p["checks"]["xdelta3"]))
    if v.get("patch"):
        L.append("  volume ISO: vcdiff.py %s, xdelta3 %s" % (v["patch"]["checks"]["vcdiff.py"], v["patch"]["checks"]["xdelta3"]))
    with open(os.path.join(out_dir, "HASHES.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def changelog_section(text, version, heading):
    """The bullet lines under '### <heading>' of '## [<version>]' of a Keep a Changelog file ([] when there are none)."""
    m = re.search(r"^## \[%s\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)" % re.escape(version), text, re.M | re.S)
    if not m:
        return []
    h = re.search(r"^### %s[^\n]*\n(.*?)(?=^### |\Z)" % re.escape(heading), m.group(1), re.M | re.S)
    if not h:
        return []
    return [b.strip() for b in re.findall(r"^- (.+(?:\n  .+)*)", h.group(1), re.M)]


def prerelease_label(version):
    """'beta' for 0.1.0-beta.1, 'release candidate' for -rc.N, the raw suffix otherwise, '' for a final version."""
    m = SEMVER.match(version)
    pre = m.group(4) if m else None
    if not pre:
        return ""
    kind = pre.split(".")[0]
    return {"beta": "beta", "alpha": "alpha", "rc": "release candidate", "dev": "development"}.get(kind, pre)


def readme_md(man, changelog_text=None):
    P, V = man["project"], man["version"]
    status = prerelease_label(V)
    ch = [int(n) for n in sorted(man["tracks"], key=int) if man["tracks"][n]["changed"]]
    chp = [n for n in ch if man["tracks"][str(n)].get("patch")]        # tracks that have a raw track patch file
    unch = [int(n) for n in sorted(man["tracks"], key=int) if not man["tracks"][n]["changed"]]
    t = man["tracks"]
    iso = man["volume_iso"]
    sect = lambda h: h["size"] // 2352
    grow = ""
    if "5" in t and t["5"]["changed"] and t["5"]["result"]["size"] > t["5"]["source"]["size"]:
        extra = (t["5"]["result"]["size"] - t["5"]["source"]["size"]) // 2352
        grow = ("\n**Disc size.** In this build track 5 is %s sectors (%.1f MB) longer than the original, so the patched\n"
                "disc is larger than a real GD-R can hold. It is meant for emulators (tested in Flycast); it cannot be burnt.\n"
                % (human(extra), extra * 2352 / 1e6))
    L = []
    w = L.append
    dev = man.get("dev_build")
    w("# %s %s%s" % (P, V, (" (%s)" % status) if status else ""))
    w("")
    if dev:
        w("> **DEVELOPMENT BUILD - not a release.** %s" % dev)
        w("")
    w("An English patch for **%s** (Sega Dreamcast, Japan, HDR-0183), applied to **your own dump** of the Japanese disc. The" % man["game"]["title"])
    w("patches are standard xdelta3 / VCDIFF (RFC 3284) files with no compression, so any xdelta tool applies them.")
    w("")
    w("| | |")
    w("|---|---|")
    w("| Version | %s%s |" % (V, (" (%s)" % status) if status else ""))
    w("| Build date | %s |" % man["build_date"])
    w("| Game | %s |" % man["game"]["title"])
    w("| Source | your own dump of the Japanese disc (BIN/CUE or GDI), or its volume ISO; the hashes of the dump this project was built against are in section 4 |")
    w("| Patch format | xdelta3 / VCDIFF (RFC 3284), uncompressed; `apply_patch.py` needs only Python 3.8+ |")
    w("| Tested | in the Flycast emulator only; real Dreamcast hardware and other emulators are untested |")
    w("| Licence | tools GPL-3.0-or-later, translated text and art CC-BY-SA-4.0, font OFL-1.1 (section 6) |")
    w("")
    if status:
        w("**Status: %s.** This is a pre-release of the English translation: it covers the whole game and was played in the emulator, but it still has" % status)
        w("known issues (section 8) and not every screen has been tested. Please report what you find (section 10).")
        w("")
    w("What it changes: the game's text (menus, dialogue, news, data tables, match commentary), repainted pictures, an English proportional font and the layout")
    w("code that makes the longer English fit. Notes for the translation (what was changed and why, the Japanese terms that were kept on purpose) are in")
    w("`TRANSLATORS_NOTES.md`; what each version changes is in `CHANGELOG.md`.")
    w("")
    w("**No original Sega pixels and no game files are distributed.** A patch is useless without the right dump, and the `.xdelta` files contain only differences. You need your own legally")
    w("obtained copy of the game; do not ask for or share the disc, the patched disc or a ROM/ISO image made from it.")
    w(grow)
    w("## 1. What you need")
    w("")
    w("A dump of the disc in ONE of these forms (what each is, exactly):")
    w("")
    w("| Your dump | Files | Patch files |")
    w("|---|---|---|")
    w("| **BIN/CUE** | one `.cue` + `%s (Track N).bin` for N = 1-5, raw 2352-byte sectors | %s |" % (TITLE_SHORT(man), "Track %s (%s bytes)" % (", ".join(map(str, chp)), human(sum(t[str(n)]["patch"]["size"] for n in chp))) if chp else "none: the volume-ISO patch is used and the raw tracks are rebuilt from it"))
    w("| **GDI** | one `.gdi` + `track01.bin`, `track02.raw`, `track03.bin`, `track04.raw`, `track05.bin`, raw 2352-byte sectors | %s |" % (
        "%s (the same patch files, %s bytes)" % (", ".join("`%s`" % t[str(n)]["gdi_name"] for n in chp), human(sum(t[str(n)]["patch"]["size"] for n in chp)))
        if chp else "none: the volume-ISO patch is used and the raw tracks are rebuilt from it"))
    w("| **Volume ISO** | ONE `.iso` of 2048-byte sectors in which sector 0 is disc LBA 45000 (`SEGA SEGAKATANA` IP.BIN first, ISO9660 descriptor at sector 16), audio track and track-5 pregap as zero sectors | the volume-ISO patch (%s bytes) |" % human(iso["patch"]["size"] if iso.get("patch") else 0))
    w("")
    w("The BIN/CUE and the GDI form use the **same raw track data**, so they use the same patch files; only the file")
    w("names differ. Tracks %s are not changed by this patch and need no patch (track 1-2 are the low-density area, track 4 is audio)."
      % ", ".join(map(str, unch)) if unch else "Every track changes.")
    w("")
    w("Other forms are NOT supported: a single `.bin` holding all tracks, per-track 2048-byte `.iso` tracks, CHD/CSO/NRG/CDI,")
    w("an ISO that starts at LBA 0. Convert such a dump to a .cue/.gdi with raw tracks first (or to the volume ISO above).")
    w("")
    w("## 2. Easiest: apply_patch.py")
    w("")
    w("`apply_patch.py` is ONE file (Python 3.8 or newer, no other packages; the xdelta decoder and the disc code are built")
    w("in). Keep it, `MANIFEST.json` and the `.xdelta` files together in one folder:")
    w("")
    w("```")
    w('python apply_patch.py "C:\\Games\\Sakatsuku 2\\Sakatsuku.cue"')
    w('python apply_patch.py "C:\\Games\\Sakatsuku 2\\disc.gdi"')
    w('python apply_patch.py "C:\\Games\\Sakatsuku 2\\Sakatsuku.iso"')
    w('python apply_patch.py disc.gdi --verify        # only report: original, already patched, or wrong dump')
    w('python apply_patch.py Sakatsuku.cue --to iso   # write the patched game as a volume ISO instead')
    w("```")
    w("")
    w("It recognises the format by content, checks every file against the hashes below, and writes the patched copy in the")
    w("same format NEXT TO your files: a new folder `<name> (%s)` with the `.cue`/`.gdi`, the copied unchanged tracks and the" % P)
    w("patched tracks (cue, gdi), or `<name> (%s).iso` (iso, or `--to iso`). Your files are never modified. Options: `--out`," % P)
    w("`--link` (hard-link unchanged tracks instead of copying), `--overwrite`. Boot the `.gdi` (or the `.cue`) in Flycast (the only emulator this patch was tested with).")
    w("")
    w("A cue/gdi dump that matches the original hashes is patched track by track (fast). A dump whose tracks differ in the")
    w("audio tracks or pregaps, but holds the same game data, is converted to the volume ISO inside the program, patched,")
    w("and the raw tracks are rebuilt from it with fresh sync/header/EDC/ECC for every changed sector and your own bytes")
    w("everywhere else (`--method iso` forces this route; the check is then on the game data, not the raw file hashes).")
    w("Disk space: about 1.2 GB for the patched disc, plus about 2 GB of temporary files on the ISO route.")
    w("")
    w("## 3. By hand with xdelta UI / DeltaPatcher / xdelta3")
    w("")
    w("Patch each changed track as its own file: **Source file** = your track file, **Patch** = the `.xdelta`, **Output**")
    w("= a NEW file in a new folder, with the SAME file name as the original (the `.cue`/`.gdi` refer to the names).")
    w("Then copy the `.cue`/`.gdi` and the unchanged tracks into the same new folder.")
    w("")
    w("| Patch | BIN/CUE source file | GDI source file | Output size |")
    w("|---|---|---|---|")
    for n in chp:
        e = t[str(n)]
        w("| `%s` | `%s` | `%s` | %s bytes |" % (e["patch"]["file"], e["redump_name"], e["gdi_name"], human(e["result"]["size"])))
    if iso["changed"]:
        w("| `%s` | (volume ISO) | (volume ISO) | %s bytes |" % (iso["patch"]["file"], human(iso["result"]["size"])))
    w("")
    w("Command line (xdelta3 3.x):")
    w("")
    w("```")
    for n in chp:
        e = t[str(n)]
        w('xdelta3 -d -s "%s" "%s" "patched\\%s"' % (e["redump_name"], e["patch"]["file"], e["redump_name"]))
    for n in chp:
        e = t[str(n)]
        w('xdelta3 -d -s "%s" "%s" "patched\\%s"      (GDI)' % (e["gdi_name"], e["patch"]["file"], e["gdi_name"]))
    if iso["changed"]:
        w('xdelta3 -d -s "Sakatsuku.iso" "%s" "Sakatsuku (EN).iso"' % iso["patch"]["file"])
    w("```")
    w("")
    x3v = (man.get("tools") or {}).get("xdelta3")
    w("The patches were checked with %s and with this release's apply_patch.py; xdelta UI and" % (x3v or "no xdelta3 (it was not installed)"))
    w("DeltaPatcher read the same standard format but were not run here. If a tool complains, use `apply_patch.py`, and")
    w("always compare the output with the hashes below.")
    w("")
    w("## 4. Hashes to compare")
    w("")
    w("`HASHES.txt` and `MANIFEST.json` list everything (CRC-32, MD5, SHA-1, SHA-256). These are the hashes of the dump this project")
    w("was built against (catalogue reference: Redump disc 27370); the tooling has not compared them with the Redump database. Short form, SHA-1:")
    w("")
    w("| File | Your dump must be | After patching |")
    w("|---|---|---|")
    for n in sorted(t, key=int):
        e = t[n]
        w("| Track %s (`%s`) | `%s` | %s |" % (n, e["gdi_name"], e["source"]["sha1"],
                                                  "`%s`" % e["result"]["sha1"] if e["changed"] else "unchanged"))
    w("| Volume ISO | `%s` | %s |" % (iso["source"]["sha1"], "`%s`" % iso["result"]["sha1"] if iso["changed"] else "unchanged"))
    w("")
    w("Sizes (bytes): " + "; ".join("track %s %s" % (n, human(t[n]["source"]["size"])) for n in sorted(t, key=int))
      + "; volume ISO %s." % human(iso["source"]["size"]))
    w("`SHA256SUMS` covers the files of this download (`sha256sum -c SHA256SUMS`).")
    w("")
    w("## 5. If the hashes differ")
    w("")
    w("* **Only an unchanged track (1, 2 or 4) differs**: harmless for this patch (apply_patch.py only warns). Different")
    w("  dumpers store the audio tracks and pregaps a little differently.")
    w("* **A changed track (3 or 5) differs in SIZE**: your dump stores the track differently (cut or extra pregap sectors,")
    w("  2048-byte sectors, merged tracks). Re-dump or convert to the layout of the dump above: track 5 must start with its 225 pregap")
    w("  sectors (file sectors 0-224), track 3 with the IP.BIN at LBA 45000.")
    w("* **Same size, different hash**: a different dump or read errors, or an already modified file. Do not patch it; a")
    w("  second dump of the same disc, or a comparison with a database entry for the game, helps to tell which.")
    w("* **The result hash differs after patching**: the source was not what the patch expects. apply_patch.py deletes such")
    w("  output; with a manual patcher delete the output file and do not use it.")
    w("* A patch file damaged in download: compare it with `SHA256SUMS`.")
    w("")
    w("## 6. Licence")
    w("")
    w("`apply_patch.py` and `verify_dist.py` are GPL-3.0-or-later (the VCDIFF code built into `apply_patch.py` is adapted from")
    w("the LMAST-Reverse project, same author; full text in `LICENSE` and `LICENSES/GPL-3.0-or-later.txt`).")
    w("The translated text, the repainted pictures and the documents are CC-BY-SA-4.0 (`LICENSES/CC-BY-SA-4.0.txt`); they are in this")
    w("download only inside the `.xdelta` files. **No original Sega pixels are distributed:** the `.xdelta` files contain only differences, and you")
    w("apply them to your own dump. The original game (its Japanese text, art, music and code) belongs to its owners and is not")
    w("licensed by this project.")
    w("")
    w("## 7. Checking this download")
    w("")
    w("`python verify_dist.py` checks the files of this folder against `SHA256SUMS` and `MANIFEST.json`;")
    w("`python verify_dist.py --disc \"your.cue\"` also patches your dump into a scratch folder and compares the result with the")
    w("hashes above.")
    w("")
    w("## 8. Known issues")
    w("")
    issues = changelog_section(changelog_text, V, "Known issues") if changelog_text else []
    if issues:
        for b in issues:
            w("* " + " ".join(b.split()))
    else:
        w("See `CHANGELOG.md`.")
    w("")
    w("The full list for this version is in `CHANGELOG.md`; `TRANSLATORS_NOTES.md` section 8 explains the limits.")
    w("")
    w("## 9. Credits")
    w("")
    w("* Translation, reverse engineering, tooling and repainted graphics: the SakaTsuku2-EN project, Nexxus Drako Multimedia.")
    w("* Thanks to Nexxus Drako and to the **Community Discord** (https://discord.gg/7DNrGye9TZ).")
    w("* English half-width glyphs: rendered from Roboto Condensed Medium, Copyright 2011 The Roboto Project Authors")
    w("  (https://github.com/googlefonts/roboto-classic), SIL Open Font License 1.1 (`LICENSES/OFL-1.1.txt`).")
    w("* The VCDIFF code in `apply_patch.py` is adapted from the LMAST-Reverse project (same author); xdelta3 (Joshua MacDonald and contributors) is used to cross-check every patch.")
    w("* Staff names in the credits were romanised with the help of public credit databases (Sega Retro, MobyGames); some readings are uncertain (section 8).")
    w("* The original game is (c) its owners; the club and competition names belong to theirs. This is an unofficial fan translation and is not affiliated with them.")
    w("")
    w("## 10. Reporting problems")
    w("")
    w("Report bugs, wrong or missing translations and screens that are still Japanese at https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/issues .")
    w("Please say which version (%s), which dump form you used, which emulator and its version, the output of `python apply_patch.py <dump> --verify`," % V)
    w("and for a text problem the screen and how you reached it (a screenshot helps). Do not attach the game, a disc image or a save file made from a patched disc.")
    return "\n".join(L) + "\n"


def TITLE_SHORT(man):
    return man["game"]["title"]


EMBED_BEGIN = "# @@EMBED-BEGIN@@"
EMBED_END = "# @@EMBED-END@@"
EMBED_MODULES = ("discformat", "vcdiff", "bincue2iso")


def single_file_apply():
    """tools/apply_patch.py with discformat.py, vcdiff.py and bincue2iso.py embedded (one stdlib-only file)."""
    with open(os.path.join(HERE, "apply_patch.py"), encoding="utf-8", newline="") as f:
        text = f.read().replace("\r\n", "\n")
    a, b = text.index(EMBED_BEGIN), text.index(EMBED_END)
    block = ["# The modules below are verbatim copies of tools/discformat.py, tools/vcdiff.py and tools/bincue2iso.py of the",
             "# SakaTsuku2-EN repository (GPL-3.0-or-later, same licence as this file), executed as modules of those names.",
             "_EMBEDDED = ["]
    for name in EMBED_MODULES:
        with open(os.path.join(HERE, name + ".py"), encoding="utf-8", newline="") as f:
            src = f.read().replace("\r\n", "\n")
        if "'''" in src or src.endswith("\\"):
            fail("%s.py cannot be embedded as a raw string (contains ''' )" % name)
        block.append("(%r, r'''%s'''),\n" % (name, src))
    block += ["]", "",
              "",
              "def _load_embedded():",
              "    import types",
              "    for name, src in _EMBEDDED:",
              "        if name in sys.modules:",
              "            continue",
              "        mod = types.ModuleType(name)",
              "        mod.__file__ = '<embedded %s.py>' % name",
              "        sys.modules[name] = mod",
              "        exec(compile(src, mod.__file__, 'exec'), mod.__dict__)",
              "",
              "",
              "_load_embedded()"]
    return text[:a] + EMBED_BEGIN + " (generated by tools/release.py: the embedded modules)\n" + "\n".join(block) + "\n" + text[b:]


def check_notes(path, allow_placeholder):
    """The translators' notes must exist; a file that still carries the marker PLACEHOLDER fails the bundle."""
    if not path or not os.path.isfile(path):
        fail("the translators' notes %s do not exist (set [bundle] translators_notes in tools/release.toml; the docs "
             "stage writes the file)" % path)
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if "PLACEHOLDER" in text:
        if not allow_placeholder:
            fail("%s still contains the marker PLACEHOLDER (the docs stage has not written the real notes yet); "
                 "pass --allow-placeholder for a development bundle" % path)
        log("  WARNING: bundling a PLACEHOLDER translators' notes file (--allow-placeholder)")


def check_changelog(path, version, strict):
    """The changelog (Keep a Changelog) must exist and, for a real release (strict), carry a `## [version]` section."""
    if not path or not os.path.isfile(path):
        fail("the changelog %s does not exist (set [bundle] changelog in tools/release.toml)" % path)
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if re.search(r"^## \[%s\]" % re.escape(version), text, re.M):
        return
    msg = "%s has no section '## [%s]' (Keep a Changelog: add it, with its date, before cutting the release)" % (path, version)
    if strict:
        fail(msg)
    log("  WARNING: " + msg)


def copy_licenses(src_dir, out_dir):
    """Copy the licence texts (REUSE layout: LICENSES/<SPDX-id>.txt) into the bundle; returns the sorted file names."""
    names = []
    if src_dir and os.path.isdir(src_dir):
        os.makedirs(os.path.join(out_dir, "LICENSES"), exist_ok=True)
        for n in sorted(os.listdir(src_dir)):
            if n.endswith(".txt") and os.path.isfile(os.path.join(src_dir, n)):
                shutil.copy2(os.path.join(src_dir, n), os.path.join(out_dir, "LICENSES", n))
                names.append(n)
    return names


OFL_NOTICE = ("\n"
              "Fonts: in a build made with --open-font on (the half-width English letters, digits and symbols) the 94 ASCII glyphs of FONT.BIN\n"
              "are bitmaps rendered from Roboto Condensed Medium, Copyright 2011 The Roboto Project Authors\n"
              "(https://github.com/googlefonts/roboto-classic), licensed under the SIL Open Font License, Version 1.1 (SPDX OFL-1.1;\n"
              "LICENSES/OFL-1.1.txt).  The bitmaps are a derivative work, redistributed under the same licence inside the .xdelta patches; the\n"
              "font itself is not distributed.  The font name is not a Reserved Font Name.\n")


def write_readme(man, out_dir, changelog=None):
    text = None
    if changelog and os.path.isfile(changelog):
        with open(changelog, encoding="utf-8", errors="replace") as f:
            text = f.read()
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme_md(man, text))


def write_docs(man, out_dir, build_text, notes=None, allow_placeholder=False, changelog=None, licenses_dir=None):
    lic = copy_licenses(licenses_dir, out_dir)
    man["bundle"] = {"changelog": bool(changelog), "licenses": lic}      # verify_dist.py checks that these files are there
    if changelog:
        shutil.copy2(changelog, os.path.join(out_dir, "CHANGELOG.md"))
    with open(os.path.join(out_dir, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=2)
        f.write("\n")
    write_hashes_txt(man, out_dir)
    write_readme(man, out_dir, changelog)
    with open(os.path.join(out_dir, "VERSION"), "w", encoding="utf-8", newline="\n") as f:
        f.write(man["version"] + "\n")
    with open(os.path.join(out_dir, "apply_patch.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(single_file_apply())
    shutil.copy2(os.path.join(HERE, "verify_dist.py"), os.path.join(out_dir, "verify_dist.py"))
    if notes:
        check_notes(notes, allow_placeholder)
        shutil.copy2(notes, os.path.join(out_dir, "TRANSLATORS_NOTES.md"))
    if os.path.exists(os.path.join(ROOT, "LICENSE")):
        shutil.copy2(os.path.join(ROOT, "LICENSE"), os.path.join(out_dir, "LICENSE"))
    with open(os.path.join(out_dir, "NOTICE.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("apply_patch.py (with its built-in VCDIFF decoder, disc format detection and sector codec) and verify_dist.py:\n"
                "SPDX-License-Identifier GPL-3.0-or-later. Copyright (C) 2026 Nexxus Drako Multimedia. The VCDIFF code is\n"
                "adapted from the LMAST-Reverse project (SRC/vcdiff.py) by the same author. Full text: LICENSE\n"
                "(https://www.gnu.org/licenses/gpl-3.0.txt)\n"
                "\n"
                "The translated text, the repainted pictures and the documents of this project (README.md, TRANSLATORS_NOTES.md,\n"
                "CHANGELOG.md) are licensed CC-BY-SA-4.0 (SPDX-License-Identifier CC-BY-SA-4.0; LICENSES/CC-BY-SA-4.0.txt).  They\n"
                "are present in this download only inside the .xdelta patches.  The original game (its Japanese text, pictures, music\n"
                "and code) belongs to its owners and is NOT licensed by this project: no original Sega pixels are distributed, the patches are\n"
                "deltas that you apply to your own dump.  Licence texts: LICENSES/.\n"
                + (OFL_NOTICE if "OFL-1.1.txt" in lic else ""))
    if build_text:
        with open(os.path.join(out_dir, "BUILD-SUMMARY.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(scrub_paths(build_text))      # no absolute local paths in a bundle file


def release_files(folder):
    out = []
    for top, _, files in os.walk(folder):
        for n in files:
            if n.endswith(".pyc"):
                continue
            out.append(os.path.relpath(os.path.join(top, n), folder).replace(os.sep, "/"))
    return sorted(out)


def write_sha256sums(folder):
    names = [n for n in release_files(folder) if n != "SHA256SUMS"]
    with open(os.path.join(folder, "SHA256SUMS"), "w", newline="\n") as f:
        for n in names:
            f.write("%s  %s\n" % (DF.hash_file(os.path.join(folder, n))["sha256"], n))


def zip_folder(folder, date):
    """Zip the folder; entry times come from --date so the zip does not depend on the clock."""
    zpath = folder + ".zip"
    base = os.path.basename(folder)
    y, mo, d = (int(x) for x in date.split("-"))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in release_files(folder):
            zi = zipfile.ZipInfo("%s/%s" % (base, n), (y, mo, d, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(os.path.join(folder, n), "rb") as f:
                z.writestr(zi, f.read(), compresslevel=9)
    with open(zpath + ".sha256", "w", newline="\n") as f:
        f.write("%s  %s\n" % (DF.hash_file(zpath)["sha256"], os.path.basename(zpath)))
    return zpath


# ----------------------------------------------------------------------------- driver
def git_info():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        head = r.stdout.strip()
        d = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
        return head + ("+dirty" if d else "")
    except OSError:
        return None


def print_source_toml():
    cfg_tracks = repo_source_tracks()
    layout = game_layout()
    out = ["# hashes of the repo's Redump-style source disc (print with: release.py --print-source-toml)"]
    for n in range(1, 6):
        h = DF.hash_file(cfg_tracks[n])
        out.append("[source.track%d]" % n)
        out += ['%s = %s' % (k, h[k] if k == "size" else '"%s"' % h[k]) for k in HASH_KEYS]
    iso = os.path.join(ROOT, "build", "release", "source.iso")
    os.makedirs(os.path.dirname(iso), exist_ok=True)
    isoexport.export_volume_iso([(layout["tracks"][n]["lba"], layout["tracks"][n]["kind"], cfg_tracks[n])
                                 for n in range(3, 6)], iso, layout["hd_base"])
    h = DF.hash_file(iso)
    out.append("[source.volume_iso]")
    out += ['%s = %s' % (k, h[k] if k == "size" else '"%s"' % h[k]) for k in HASH_KEYS]
    print("\n".join(out))


def notes_path(cfg):
    rel = (cfg.get("bundle") or {}).get("translators_notes")
    if not rel:
        fail("tools/release.toml has no [bundle] translators_notes path")
    return os.path.normpath(os.path.join(ROOT, rel))


def bundle_path(cfg, key):
    rel = (cfg.get("bundle") or {}).get(key)
    if not rel:
        fail("tools/release.toml has no [bundle] %s path" % key)
    return os.path.normpath(os.path.join(ROOT, rel))


def print_dev_toml(path, name):
    """The result hashes of a built disc as a [dev.NAME] table for release.toml (clearly a development record)."""
    disc = DF.open_disc(os.path.abspath(path), 5)
    layout = game_layout()
    out = ["# DEVELOPMENT hashes of the trial disc %s (not a release; regenerate with release.py --print-dev-toml)" % os.path.basename(path),
           "[dev.%s]" % name, 'note = "development record, not a release"']
    for n in range(1, 6):
        h = DF.hash_file(disc.tracks[n])
        out.append("[dev.%s.track%d]" % (name, n))
        out += ["%s = %s" % (k, h[k] if k == "size" else '"%s"' % h[k]) for k in HASH_KEYS]
    tmp = os.path.join(ROOT, "build", "rel_dev_toml.tmp.iso")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    try:
        isoexport.export_volume_iso([(layout["tracks"][n]["lba"], layout["tracks"][n]["kind"], disc.tracks[n])
                                     for n in range(3, 6)], tmp, layout["hd_base"])
        h = DF.hash_file(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    out.append("[dev.%s.volume_iso]" % name)
    out += ["%s = %s" % (k, h[k] if k == "size" else '"%s"' % h[k]) for k in HASH_KEYS]
    print("\n".join(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="the source disc: .cue, .gdi or volume .iso (default: the repo's Redump cue)")
    ap.add_argument("--date", help="build date, YYYY-MM-DD (required; never read from the clock)")
    ap.add_argument("--version", help="release version (default: tools/VERSION)")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "release"))
    ap.add_argument("--reuse-build", action="store_true", help="reuse <work>/disc if it holds a finished build")
    ap.add_argument("--no-xdelta3", action="store_true", help="skip the xdelta3 cross-check")
    ap.add_argument("--print-source-toml", action="store_true", help="print the [source.*] hash tables for release.toml and exit")
    ap.add_argument("--print-dev-toml", metavar="DISC", help="print a [dev.NAME] hash table (result hashes of a built disc .gdi/.cue) and exit")
    ap.add_argument("--dev-name", default="trial", help="NAME of the [dev.NAME] table (--print-dev-toml, --built-disc)")
    ap.add_argument("--built-disc", metavar="DISC", help="use this already built disc (.gdi/.cue of a trial build) as the "
                    "patched side instead of running tools/build_patch.py; the bundle is marked as a development build")
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="bundle a TRANSLATORS_NOTES.md that still contains the marker PLACEHOLDER (development bundles)")
    ap.add_argument("--cleanup-work", action="store_true", help="delete the exported ISOs in --work when the bundle is done")
    ap.add_argument("--no-raw-patches", action="store_true", help="ship only the volume-ISO patch (smaller download): BIN/CUE and GDI players go through the ISO and the raw tracks are rebuilt")
    a, bp_args = ap.parse_known_args(argv)
    if a.print_source_toml:
        print_source_toml()
        return 0
    if a.print_dev_toml:
        print_dev_toml(a.print_dev_toml, a.dev_name)
        return 0
    if not a.date or not re.match(r"^\d{4}-\d{2}-\d{2}$", a.date):
        fail("--date YYYY-MM-DD is required")
    try:
        import datetime
        if datetime.date(*(int(x) for x in a.date.split("-"))).year < 1980:      # zip entries cannot hold earlier dates
            raise ValueError("year before 1980")
    except ValueError as e:
        fail("--date %s is not a real calendar date (%s)" % (a.date, e))
    cfg = load_config()
    if not bp_args:        # no build option on the command line: the standard release flags of tools/release.toml [build]
        bp_args = [str(x) for x in cfg.get("build", {}).get("standard_flags", [])]
        log("build flags from tools/release.toml [build] standard_flags: %s" % " ".join(bp_args))
    notes = notes_path(cfg)
    check_notes(notes, a.allow_placeholder)
    version = a.version or read_version()
    if not SEMVER.match(version):
        fail("version %r is not a semantic version" % version)
    changelog = bundle_path(cfg, "changelog")
    check_changelog(changelog, version, strict=not a.built_disc)
    licenses_dir = bundle_path(cfg, "licenses_dir")
    layout = game_layout()
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    t_start = time.time()
    repo_cue = os.path.join(ROOT, TITLE + ".cue")
    source = a.source or repo_cue
    log("== 1. source disc ==")
    disc, src_in = verify_source(source, cfg, layout)
    log("  %s matches the recorded hashes" % source)
    repo_tracks = repo_source_tracks()
    if disc.kind == "cue" and os.path.normcase(os.path.abspath(source)) == os.path.normcase(repo_cue):
        src_hashes = src_in
    else:
        log("  the build reads the repo's own Redump tracks (tools/discbuild.py); checking those too")
        _, src_hashes = verify_source(repo_cue, cfg, layout)
    dev_note = None
    if a.built_disc:
        log("== 2. built disc given: %s (no build_patch.py run) ==" % a.built_disc)
        bd = DF.open_disc(os.path.abspath(a.built_disc), 5)
        if bd.kind == "iso":
            fail("--built-disc needs a .gdi or .cue")
        built_tracks = dict(bd.tracks)
        info = {k: None for k in BUILD_RE}
        build_text = "development bundle: the patched side is the disc %s (made by someone else, no build log)\n" % a.built_disc
        dev_note = ("Made from the trial disc %s, not from a clean tools/release.py build; the hashes are those of that disc. "
                    "Do not publish." % os.path.basename(a.built_disc))
    else:
        log("== 2. build the patched disc ==")
        built_tracks, info, build_text = run_build(work, bp_args, a.reuse_build)
    if info["records"]:
        log("  translation DB: %s records, %s with English" % info["records"])
    built_hashes = {}
    for n in range(1, 6):
        built_hashes[n] = DF.hash_file(built_tracks[n])
        log("  built track %d: %s bytes, SHA-1 %s%s" % (n, human(built_hashes[n]["size"]), built_hashes[n]["sha1"],
                                                         "" if built_hashes[n]["sha1"] != src_hashes[n]["sha1"] else "  (unchanged)"))
    log("== 3. volume ISO ==")
    t0 = time.time()
    hd = [(layout["tracks"][n]["lba"], layout["tracks"][n]["kind"]) for n in range(3, 6)]
    src_iso = os.path.join(work, "source.iso")
    built_iso = os.path.join(work, "%s.iso" % PROJECT)
    isoexport.export_volume_iso([(hd[i][0], hd[i][1], repo_tracks[3 + i]) for i in range(3)], src_iso, layout["hd_base"])
    src_hashes["iso"] = DF.hash_file(src_iso)
    m = compare("exported source volume ISO", src_iso, src_hashes["iso"], recorded(cfg, "volume_iso"))
    if m:
        fail(m)
    isoexport.export_volume_iso([(hd[i][0], hd[i][1], built_tracks[3 + i]) for i in range(3)], built_iso, layout["hd_base"])
    built_hashes["iso"] = DF.hash_file(built_iso)
    log("  exported source and built ISO in %.0f s; built ISO %s bytes" % (time.time() - t0, human(built_hashes["iso"]["size"])))
    log("== 4. patches ==")
    x3 = None if a.no_xdelta3 else find_xdelta3()
    log("  xdelta3: %s" % (x3 or "not found, cross-check skipped"))
    out_dir = os.path.join(os.path.abspath(a.out), "%s-%s" % (PROJECT, version))
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    src_files = dict(repo_tracks)
    src_files["iso"] = src_iso
    built_files = dict(built_tracks)
    built_files["iso"] = built_iso
    x3ver = None
    if x3:
        r = subprocess.run([x3, "-V"], capture_output=True, text=True, errors="replace")
        x3ver = ((r.stdout + r.stderr).strip().splitlines() or [""])[0].split(",")[0] or "xdelta3"
    extra = {"tools": {"xdelta3": x3ver, "python": sys.version.split()[0]}, "build": {"build_patch_args": bp_args,
                       "translation_records": int(info["records"][0]) if info["records"] else None,
                       "translation_records_with_english": int(info["records"][1]) if info["records"] else None,
                       "patch_digest": info["digest"][0] if info["digest"] else None,
                       "files_changed": int(info["files"][0]) if info["files"] else None,
                       "disc_end_lba": [int(info["disc"][2]), int(info["disc"][3])] if info["disc"] else None}}
    if a.built_disc:
        dev = (cfg.get("dev") or {}).get(a.dev_name)
        if dev:
            bad = []
            for key, h in [("track%d" % n, built_hashes[n]) for n in range(1, 6)] + [("volume_iso", built_hashes["iso"])]:
                m = compare(key, "built", h, {k: dev[key][k] for k in HASH_KEYS}) if key in dev else "%s missing" % key
                if m:
                    bad.append(m)
            log("  [dev.%s] hashes in release.toml %s" % (a.dev_name, "MATCH the built disc" if not bad else
                                                          "DIFFER from the built disc (the trial disc changed since they were recorded):\n    " + "\n    ".join(bad)))
        else:
            log("  no [dev.%s] table in release.toml (--print-dev-toml prints one)" % a.dev_name)
        extra["build"]["built_disc"] = os.path.basename(a.built_disc)
    man = produce(layout, version, a.date, src_files, src_hashes, built_files, built_hashes, out_dir, work,
                  extra=extra, x3=x3, git_commit=git_info(), build_text=build_text, notes=notes,
                  allow_placeholder=a.allow_placeholder, dev_note=dev_note, raw_patches=not a.no_raw_patches,
                  changelog=changelog, licenses_dir=licenses_dir)
    for top, dirs, _ in os.walk(out_dir):          # bytecode of the helper scripts must never be shipped
        for d in [d for d in dirs if d == "__pycache__"]:
            shutil.rmtree(os.path.join(top, d), ignore_errors=True)
    bad = local_paths_in(out_dir)
    if bad:
        fail("absolute local paths found in the bundle files: %s" % ", ".join(bad))
    write_sha256sums(out_dir)
    zpath = zip_folder(out_dir, a.date)
    if a.cleanup_work:
        for p in (src_iso, built_iso):
            if os.path.exists(p):
                os.remove(p)
    log("== done in %.0f s ==" % (time.time() - t_start))
    log("  %s" % out_dir)
    for n in release_files(out_dir):
        log("    %12s  %s" % (human(os.path.getsize(os.path.join(out_dir, n))), n))
    log("  %s  %s bytes" % (zpath, human(os.path.getsize(zpath))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
