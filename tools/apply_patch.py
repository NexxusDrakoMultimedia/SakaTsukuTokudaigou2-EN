# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Apply the SakaTsuku2-EN English patch to your own dump of the Japanese disc.

One file, Python 3.8 or newer, standard library only. It needs MANIFEST.json and the .xdelta patch files of the
release in the same folder. The VCDIFF decoder, the disc format detection and the sector codec are built into
this file (release builds embed them; they are the author's GPL-3.0-or-later code, see NOTICE.txt).

    python apply_patch.py "My Game.cue"          # BIN/CUE (Redump): .cue + one raw .bin per track
    python apply_patch.py disc.gdi               # GDI with raw track01.bin ... track05.bin
    python apply_patch.py "My Game.iso"          # one 2048-byte 'volume ISO' (see README.md)
    python apply_patch.py disc.gdi --verify      # only report: original, already patched, or wrong dump
    python apply_patch.py "My Game.cue" --to iso # write the patched game as a volume ISO instead

The input is recognised by content and checked against the SHA-1 / SHA-256 hashes of the original dump that the
release records. A BIN/CUE or GDI dump that matches is patched track by track. If your tracks differ (another
dumper stored the audio tracks or pregaps differently) but the game data is the same, the dump is converted to the
volume ISO inside this program, the ISO is patched and the raw tracks are rebuilt from it (sync, header, EDC and ECC of
every changed sector, everything else is copied from your own tracks). `--method iso` forces that route.

The patched copy is written next to your files in the SAME format (or as ISO with --to iso), never over them: a new
folder "<name> (SakaTsuku2-EN)" with the .cue/.gdi, the unchanged tracks and the patched tracks, or
"<name> (SakaTsuku2-EN).iso". Every result is checked against the hash the release was built with before it is kept.
Nothing is written when your dump does not match. Exit status: 0 success, 1 problem, 2 bad command line.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "patcher")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# @@EMBED-BEGIN@@ (release.py replaces everything up to the end marker with the embedded modules)
# @@EMBED-END@@
import discformat as DF   # noqa: E402
import vcdiff             # noqa: E402
import bincue2iso as BC   # noqa: E402


def say(*a):
    print(*a, flush=True)


def human(n):
    return "{:,}".format(n)


def load_manifest(path):
    with open(path, "rb") as f:
        m = json.loads(f.read().decode("utf-8"))
    if m.get("manifest_version") not in (1, 2):
        raise DF.DiscError("%s is not a manifest this program understands" % path)
    return m


def _same(h, ref):
    return h["size"] == ref["size"] and h["sha1"] == ref["sha1"] and h["sha256"] == ref["sha256"]


def classify(h, entry):
    """'original', 'patched' or 'unknown' for the hash dict of a file against a manifest entry."""
    if _same(h, entry["source"]):
        return "original"
    if _same(h, entry["result"]):
        return "patched"
    return "unknown"


class Progress:
    def __init__(self, label):
        self.label, self.shown = label, -1
        self.t0 = time.time()

    def __call__(self, done, total):
        pct = 100 * done // total if total else 100
        if pct // 10 != self.shown:
            self.shown = pct // 10
            say("    %s %d%%" % (self.label, pct))


def hash_with_progress(path, label):
    return DF.hash_file(path, Progress(label))


def mismatch_text(label, path, h, entry):
    s, r = entry["source"], entry["result"]
    lines = ["%s: %s" % (label, path),
             "    your file     : %s bytes, SHA-1 %s" % (human(h["size"]), h["sha1"]),
             "    original dump : %s bytes, SHA-1 %s" % (human(s["size"]), s["sha1"])]
    if r["sha1"] != s["sha1"]:
        lines.append("    patched result: %s bytes, SHA-1 %s" % (human(r["size"]), r["sha1"]))
    if h["size"] != s["size"]:
        lines.append("    The size differs (%s bytes %s): a different dump or a different way of storing the same\n"
                     "    disc (pregap sectors, 2048-byte instead of 2352-byte sectors, a cut or padded file)."
                     % (human(abs(h["size"] - s["size"])), "more" if h["size"] > s["size"] else "less"))
    else:
        lines.append("    Same size, different content: a different dump (re-dump, or bad sectors) or a file that was\n"
                     "    already modified.")
    return "\n".join(lines)


def check_raw(disc, man):
    """Hash every track file; returns ({n: hash}, {n: state}) and prints a table."""
    hashes, states = {}, {}
    for n in sorted(disc.tracks, key=int):
        e = man["tracks"][str(n)]
        path = disc.tracks[n]
        say("  track %d  %-48s" % (n, os.path.basename(path)))
        hashes[n] = hash_with_progress(path, "hashing")
        states[n] = classify(hashes[n], e)
        say("    -> %s%s" % (states[n], "" if states[n] != "unknown" else "  (SHA-1 %s)" % hashes[n]["sha1"]))
    return hashes, states


def required_tracks(man):
    return [int(n) for n in sorted(man["tracks"], key=int) if man["tracks"][n]["changed"]]


def decide_raw(man, states):
    """'original'|'patched'|'mixed'|'bad' over the tracks the patch changes."""
    req = required_tracks(man)
    sts = [states[n] for n in req]
    if not req:
        return "original"
    if "unknown" in sts:
        return "bad"
    if all(s == "patched" for s in sts):
        return "patched"
    if all(s == "original" for s in sts):
        return "original"
    return "mixed"


def out_paths_raw(disc, out_dir):
    """{n: output path} mirroring the names in the sheet; refuses anything that would leave out_dir."""
    res = {}
    base = os.path.dirname(disc.sheet)
    for e in disc.entries:
        rel = os.path.relpath(e["file"], base)
        if rel.startswith(".."):
            raise DF.DiscError("track file %s is outside the folder of %s; move the disc into one folder first"
                               % (e["file"], disc.sheet))
        res[e["track"]] = os.path.join(out_dir, rel)
    return res


def read_patch(patch_path, pe):
    if not os.path.exists(patch_path):
        raise DF.DiscError("the patch file %s is missing (keep the .xdelta files next to apply_patch.py)" % patch_path)
    with open(patch_path, "rb") as f:
        patch = f.read()
    if hashlib.sha1(patch).hexdigest() != pe["sha1"]:
        raise DF.DiscError("%s is damaged or not the patch of this release (SHA-1 differs); download it again"
                           % patch_path)
    return patch


def preflight_patches(man, patch_dir, method, req, to_iso):
    """Check every patch file that the chosen route needs (present, SHA-1) BEFORE anything is written, so that a
    missing or damaged download does not leave a half-written output folder behind."""
    need = []
    if (method == "iso" or to_iso) and man["volume_iso"].get("changed"):
        need.append(man["volume_iso"]["patch"])
    if method == "raw" and not to_iso:
        need.extend(man["tracks"][str(n)]["patch"] for n in req)
    for pe in need:
        read_patch(os.path.join(patch_dir, pe["file"]), pe)


def apply_vcdiff(src_path, patch, tmp, entry, label):
    """Decode `patch` against src_path into tmp and check the hash of the result against entry['result']."""
    with open(src_path, "rb") as fs, open(tmp, "w+b") as fo:
        vcdiff.decode(fs, patch, fo, Progress("patching"))
    h = hash_with_progress(tmp, "checking result")
    if not _same(h, entry["result"]):
        raise DF.DiscError("%s: the patched file does not have the expected hash (SHA-1 %s, expected %s); "
                           "nothing was written" % (label, h["sha1"], entry["result"]["sha1"]))
    return h


def write_patched(src_path, patch_path, out_path, entry, label, overwrite):
    if os.path.exists(out_path) and not overwrite:
        raise DF.DiscError("%s already exists (use --overwrite to replace it)" % out_path)
    if os.path.realpath(out_path) == os.path.realpath(src_path):
        raise DF.DiscError("refusing to overwrite the source file %s" % src_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    patch = read_patch(patch_path, entry["patch"])
    tmp = out_path + ".partial"
    t0 = time.time()
    say("  applying %s ..." % os.path.basename(patch_path))
    try:
        apply_vcdiff(src_path, patch, tmp, entry, label)
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    say("  wrote %s (%s bytes, %.0f s)" % (out_path, human(entry["result"]["size"]), time.time() - t0))


def copy_or_link(src, dst, link, overwrite):
    if os.path.exists(dst):
        if not overwrite:
            raise DF.DiscError("%s already exists (use --overwrite to replace it)" % dst)
        os.remove(dst)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    if link:
        try:
            os.link(src, dst)
            return "linked"
        except OSError:
            pass
    shutil.copyfile(src, dst)
    return "copied"


# ----------------------------------------------------------------------------- cooking the player's dump
def cook_player_disc(disc, man, dest):
    """Export the player's raw tracks to the volume ISO `dest` (bincue2iso). Returns its hash dict."""
    lay = man["layout"]
    tracks = []
    for e in disc.entries:
        n = e["track"]
        if disc.kind == "gdi":
            kind, lba = ("data" if e["ctl"] == 4 else "audio"), e["lba"]
        else:
            L = lay["tracks"][str(n)]
            kind, lba = L["kind"], L["lba"]
        tracks.append(BC.Track(n, kind, e["file"], lba, 2352))
    say("  converting your tracks to the volume ISO (2048-byte sectors) ...")
    t0 = time.time()
    try:
        sectors, st = BC.write_volume(tracks, dest, False, man["layout"]["hd_base"])
    except BC.DumpError as e:
        raise DF.DiscError(str(e))
    say("    %s sectors in %.0f s (%s)" % (human(sectors), time.time() - t0, st.line()))
    return hash_with_progress(dest, "hashing the ISO")


def rebuild_info(man, n):
    rb = man.get("raw_rebuild") or {}
    return rb.get(str(n))


# ----------------------------------------------------------------------------- output paths
def default_out_dir(disc, man, a):
    stem = os.path.splitext(os.path.basename(disc.sheet))[0]
    out_dir = os.path.abspath(a.out) if a.out else os.path.join(os.path.dirname(disc.sheet), "%s (%s)" % (stem, man["project"]))
    if os.path.normcase(out_dir) == os.path.normcase(os.path.dirname(disc.sheet)):
        raise DF.DiscError("the output folder must not be the folder of the source disc (%s); use --out" % out_dir)
    return out_dir


def default_out_iso(src_path, man, a):
    stem = os.path.splitext(os.path.basename(src_path))[0]
    return os.path.abspath(a.out) if a.out else os.path.join(os.path.dirname(src_path), "%s (%s).iso" % (stem, man["project"]))


# ----------------------------------------------------------------------------- raw (cue / gdi) input
def run_raw(disc, man, a, patch_dir):
    say("Checking %d track files of %s (%s):" % (len(disc.tracks), os.path.basename(disc.sheet), disc.kind))
    hashes, states = check_raw(disc, man)
    state = decide_raw(man, states)
    req = required_tracks(man)
    for n in sorted(disc.tracks):
        if states[n] == "unknown":
            e = man["tracks"][str(n)]
            kind = "REQUIRED by the track patch" if n in req else "not changed by this patch, so only a warning"
            say(mismatch_text("track %d (%s)" % (n, kind), disc.tracks[n], hashes[n], e))
    iso_e = man["volume_iso"]
    can_iso = bool(iso_e.get("changed")) and bool(man.get("raw_rebuild")) and all(rebuild_info(man, n) for n in req)
    method = a.method
    if state == "bad":
        # not the reference dump. The game data may still be the same: compare the cooked volume ISO
        if not iso_e.get("changed"):
            say("\nERROR: a track that this patch needs is not the dump it was made for. Nothing was written.")
            return 1
        say("\nA track that the track patches need differs. Checking whether the GAME DATA is the same anyway ...")
        tmp = os.path.join(os.path.dirname(disc.sheet), os.path.splitext(os.path.basename(disc.sheet))[0] + ".cooked.tmp")
        try:
            hi = cook_player_disc(disc, man, tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        st = classify(hi, iso_e)
        if st == "unknown":
            say(mismatch_text("the volume ISO made from your tracks", "(temporary)", hi, iso_e))
            say("\nERROR: your dump holds different game data from the one this patch was made for. Nothing was written.\n"
                "See README.md, 'If the hashes differ'.")
            return 1
        say("    -> %s: the game data matches; your tracks are stored differently from the reference dump" % st)
        state = st
        method = "iso"
        reference = False
    else:
        reference = True
    if a.verify:
        if state == "original":
            say("\nOK: an unpatched disc this patch applies to%s." % (
                " (tracks %s will change)" % ", ".join(map(str, req)) if reference else " (via the volume ISO route)"))
        elif state == "patched":
            say("\nOK: this disc is already patched (version %s)." % man["version"])
        else:
            say("\nMIXED: some tracks are patched and others are not; start again from the original dump.")
            return 1
        return 0
    if state == "patched":
        say("\nThis disc is already patched (version %s); nothing to do." % man["version"])
        return 0
    if state == "mixed":
        say("\nERROR: some of the required tracks are already patched and others are not. Use the original dump.")
        return 1
    if not req and not iso_e.get("changed"):
        say("\nThis release changes no track (the translation database was empty); nothing to do.")
        return 0
    to_iso = a.to == "iso"
    have_raw = all(man["tracks"][str(n)].get("patch") for n in req)
    if method == "auto":
        method = "raw" if have_raw else "iso"
    if method == "raw" and not have_raw and not to_iso:
        raise DF.DiscError("this release has no raw track patches; use --method iso (the default for this release)")
    if (method == "iso" or to_iso) and not iso_e.get("changed"):
        raise DF.DiscError("this release has no volume ISO patch")
    if method == "iso" and not to_iso and not can_iso:
        raise DF.DiscError("this release cannot rebuild raw tracks from the ISO; use --method raw")
    preflight_patches(man, patch_dir, method, req, to_iso)
    if to_iso:
        out = default_out_iso(disc.sheet, man, a)
        return make_iso_output(disc, man, a, patch_dir, hashes, states, out, reference)
    out_dir = default_out_dir(disc, man, a)
    outs = out_paths_raw(disc, out_dir)
    if os.path.exists(os.path.join(out_dir, os.path.basename(disc.sheet))) and not a.overwrite:
        raise DF.DiscError("%s already holds a copy (use --overwrite or choose another --out)" % out_dir)
    say("\nWriting the patched disc to %s (route: %s)" % (out_dir, "track patches" if method == "raw" else "volume ISO"))
    made_dir = not os.path.isdir(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    sheet_out = os.path.join(out_dir, os.path.basename(disc.sheet))
    fresh = [p for p in [sheet_out] + [outs[n] for n in sorted(outs)] if not os.path.exists(p)]
    try:
        shutil.copyfile(disc.sheet, sheet_out)
        say("  %s: copied" % os.path.basename(disc.sheet))
        if method == "raw":
            for n in sorted(disc.tracks):
                e = man["tracks"][str(n)]
                if e["changed"]:
                    write_patched(disc.tracks[n], os.path.join(patch_dir, e["patch"]["file"]), outs[n], e, "track %d" % n,
                                  a.overwrite)
                else:
                    how = copy_or_link(disc.tracks[n], outs[n], a.link, a.overwrite)
                    say("  track %d: unchanged, %s" % (n, how))
        else:
            run_via_iso_tracks(disc, man, a, patch_dir, outs, hashes, reference, out_dir)
    except BaseException:
        # a failed run must not leave something that looks like a finished disc
        for p in fresh:
            if os.path.exists(p):
                os.remove(p)
        if made_dir:
            try:
                os.rmdir(out_dir)
            except OSError:
                pass
        say("  (the files of this run were removed)")
        raise
    say("\nDone. Open %s in your emulator." % sheet_out)
    return 0


def patched_iso_from(src_iso, man, patch_dir, dest):
    e = man["volume_iso"]
    patch = read_patch(os.path.join(patch_dir, e["patch"]["file"]), e["patch"])
    say("  applying %s ..." % e["patch"]["file"])
    apply_vcdiff(src_iso, patch, dest, e, "volume ISO")


def make_iso_output(disc, man, a, patch_dir, hashes, states, out, reference):
    """Patched volume ISO from a raw dump (--to iso)."""
    if os.path.exists(out) and not a.overwrite:
        raise DF.DiscError("%s already exists (use --overwrite to replace it)" % out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    cooked, tmp = out + ".cooked.tmp", out + ".partial"
    try:
        hi = cook_player_disc(disc, man, cooked)
        if not _same(hi, man["volume_iso"]["source"]):
            raise DF.DiscError("the volume ISO made from your tracks is not the original one (SHA-1 %s, expected %s)"
                               % (hi["sha1"], man["volume_iso"]["source"]["sha1"]))
        patched_iso_from(cooked, man, patch_dir, tmp)
        os.replace(tmp, out)
    finally:
        for p in (cooked, tmp):
            if os.path.exists(p):
                os.remove(p)
    say("\nDone. %s (%s bytes)" % (out, human(man["volume_iso"]["result"]["size"])))
    return 0


def run_via_iso_tracks(disc, man, a, patch_dir, outs, hashes, reference, out_dir):
    """cue/gdi output through the volume ISO: cook, patch, rebuild the changed raw tracks."""
    lay = man["layout"]
    cooked, patched = os.path.join(out_dir, "cooked-source.tmp"), os.path.join(out_dir, "cooked-patched.tmp")
    try:
        hi = cook_player_disc(disc, man, cooked)
        if not _same(hi, man["volume_iso"]["source"]):
            raise DF.DiscError("the volume ISO made from your tracks is not the original one (SHA-1 %s, expected %s)"
                               % (hi["sha1"], man["volume_iso"]["source"]["sha1"]))
        patched_iso_from(cooked, man, patch_dir, patched)
        os.remove(cooked)
        t0 = time.time()
        for n in sorted(disc.tracks):
            e = man["tracks"][str(n)]
            if not e["changed"]:
                how = copy_or_link(disc.tracks[n], outs[n], a.link, a.overwrite)
                say("  track %d: unchanged, %s" % (n, how))
                continue
            rb = rebuild_info(man, n)
            if os.path.exists(outs[n]) and not a.overwrite:
                raise DF.DiscError("%s already exists (use --overwrite to replace it)" % outs[n])
            say("  track %d: rebuilding the raw sectors from the patched ISO ..." % n)
            tmp = outs[n] + ".partial"
            try:
                enc = BC.rebuild_raw_track(disc.tracks[n], patched, tmp, lay["tracks"][str(n)]["lba"], lay["hd_base"],
                                           e["result"]["size"] // BC.SS, rb.get("encode", []), Progress("rebuilding"))
                if reference:
                    h = hash_with_progress(tmp, "checking result")
                    if not _same(h, e["result"]):
                        raise DF.DiscError("track %d: the rebuilt track does not have the expected hash (SHA-1 %s, expected %s); "
                                           "nothing was written" % (n, h["sha1"], e["result"]["sha1"]))
                os.replace(tmp, outs[n])
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
            say("  wrote %s (%s sectors written new, %.0f s)" % (outs[n], human(enc), time.time() - t0))
        if not reference:
            say("  your tracks are not the reference dump, so the raw files cannot be compared with the release hashes;\n"
                "  checking the game data of the result instead ...")
            sheet_out = os.path.join(out_dir, os.path.basename(disc.sheet))
            d2 = DF.open_disc(sheet_out, len(man["tracks"]))
            hi2 = cook_player_disc(d2, man, cooked)
            if not _same(hi2, man["volume_iso"]["result"]):
                raise DF.DiscError("the game data of the rebuilt disc is not the patched volume ISO; do not use it")
            say("    the game data of the result matches the patched volume ISO")
    finally:
        for p in (cooked, patched):
            if os.path.exists(p):
                os.remove(p)


# ----------------------------------------------------------------------------- volume ISO input
def run_iso(disc, man, a, patch_dir):
    e = man["volume_iso"]
    say("Checking %s (volume ISO):" % os.path.basename(disc.iso))
    h = hash_with_progress(disc.iso, "hashing")
    st = classify(h, e)
    say("    -> %s" % st)
    if st == "unknown":
        say(mismatch_text("volume ISO", disc.iso, h, e))
        say("\nThe patch needs the exact 'volume ISO' described in README.md (sector 0 = LBA 45000, audio track and\n"
            "pregap as zero sectors). If your ISO was made differently, patch the raw tracks (.cue/.gdi) instead.")
        return 1
    if a.verify:
        say("\nOK: %s." % ("an unpatched volume ISO this patch applies to" if st == "original"
                           else "this ISO is already patched (version %s)" % man["version"]))
        return 0
    if st == "patched":
        say("\nThis ISO is already patched (version %s); nothing to do." % man["version"])
        return 0
    if not e["changed"]:
        say("\nThis release changes nothing on the disc (the translation database was empty); nothing to do.")
        return 0
    if a.to not in ("same", "iso"):
        raise DF.DiscError("an ISO input can only produce an ISO (--to iso)")
    out = default_out_iso(disc.iso, man, a)
    write_patched(disc.iso, os.path.join(patch_dir, e["patch"]["file"]), out, e, "volume ISO", a.overwrite)
    say("\nDone. %s" % out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Apply the SakaTsuku2-EN patch to your own dump (.cue, .gdi or volume .iso).")
    ap.add_argument("disc", help="the .cue, .gdi or .iso of your dump of the Japanese disc")
    ap.add_argument("--manifest", default=os.path.join(HERE, "MANIFEST.json"), help="default: MANIFEST.json next to this file")
    ap.add_argument("--out", help="output folder (cue/gdi) or file (iso); default: next to the source")
    ap.add_argument("--verify", action="store_true", help="only check the disc (original / already patched / wrong)")
    ap.add_argument("--to", choices=("same", "iso"), default="same",
                    help="output form: same as the input (default) or a volume ISO (from a cue/gdi dump)")
    ap.add_argument("--method", choices=("auto", "raw", "iso"), default="auto",
                    help="cue/gdi input: patch the raw tracks directly (raw), or convert to the volume ISO, patch it and "
                         "rebuild the raw tracks (iso); auto = raw when your tracks match the reference dump, iso otherwise")
    ap.add_argument("--link", action="store_true", help="hard-link unchanged tracks instead of copying them (same drive only)")
    ap.add_argument("--overwrite", action="store_true", help="replace files in the output location (never the source)")
    a = ap.parse_args(argv)
    try:
        man = load_manifest(a.manifest)
        patch_dir = os.path.dirname(os.path.abspath(a.manifest))
        say("%s %s  (built %s)" % (man["project"], man["version"], man["build_date"]))
        disc = DF.open_disc(a.disc, len(man["tracks"]))
        if disc.kind == "iso":
            return run_iso(disc, man, a, patch_dir)
        return run_raw(disc, man, a, patch_dir)
    except DF.DiscError as e:
        say("ERROR: %s" % e)
        return 1
    except (ValueError, OSError) as e:
        say("ERROR: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
