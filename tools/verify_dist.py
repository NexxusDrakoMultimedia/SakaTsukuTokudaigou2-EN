# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Acceptance check of a SakaTsuku2-EN release folder (standard library only, Python 3.8+).

    python verify_dist.py                              # check this folder: SHA256SUMS, manifest, patches, scripts
    python verify_dist.py --source "game.cue"          # ... and patch YOUR dump in every supported way (scratch folder)
    python verify_dist.py --disc "x.gdi" [--disc ...]  # patch these discs as they are (one run each)
    python verify_dist.py --dist dist/SakaTsuku2-EN-0.1.0-dev --source ... --built build/trial/prop5/prop5.gdi

Run from a release folder it needs nothing else. --dist names another folder (maintainers run it from tools/ with
--dist). --source takes a Redump-style .cue of the ORIGINAL disc and plays the player in every supported form with the
release's own apply_patch.py (a subprocess):
  cue    BIN/CUE input, track patches            cue-iso   BIN/CUE input through the volume ISO (raw tracks rebuilt)
  gdi    synthetic GDI of the same tracks        gdi-iso   the same through the volume ISO
  iso    the volume ISO made from the source     cue->iso  BIN/CUE input, --to iso
and compares every produced file with the hashes the manifest promises (and, with --built, byte for byte with that
built disc). Nothing is written outside --scratch (default: a folder next to this file named verify_scratch).
Exit status 0 when every check passed.
"""
import argparse
import ast
import filecmp
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True          # loading apply_patch.py from the release folder must not leave a __pycache__ there

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()
FAILS = []
STDLIB_OK = {"argparse", "hashlib", "json", "os", "shutil", "sys", "time", "re", "zlib", "io", "struct", "operator",
             "shlex", "types", "lzma", "__future__"}


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


def check(cond, msg):
    log(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)
    return cond


def hash_file(path):
    h1, h2 = hashlib.sha1(), hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h1.update(b)
            h2.update(b)
            n += len(b)
    return n, h1.hexdigest(), h2.hexdigest()


def same(h, ref):
    return h[0] == ref["size"] and h[1] == ref["sha1"] and h[2] == ref["sha256"]


def load_py(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_apply(dist, disc, *extra):
    t = time.time()
    r = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", os.path.join(dist, "apply_patch.py"), disc] + list(extra),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    log("  apply_patch.py %s %s: exit %d in %.0f s" % (os.path.basename(disc), " ".join(extra[:4]), r.returncode, time.time() - t))
    return r.returncode, r.stdout + r.stderr


def link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


# ----------------------------------------------------------------------------- 1. the folder
def check_folder(dist, man):
    sums = os.path.join(dist, "SHA256SUMS")
    if check(os.path.exists(sums), "SHA256SUMS exists"):
        bad, n = [], 0
        with open(sums, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                want, name = line.rstrip("\n").split("  ", 1)
                n += 1
                p = os.path.join(dist, name)
                if not os.path.exists(p) or hash_file(p)[2] != want:
                    bad.append(name)
        check(not bad and n > 0, "SHA256SUMS: %d files verified%s" % (n, "" if not bad else ", BAD: %s" % bad))
        # nothing may sit in the folder that SHA256SUMS does not list (a stray file would be shipped with the folder)
        listed = set()
        with open(sums, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    listed.add(line.rstrip("\r\n").split("  ", 1)[1].replace("\\", "/"))
        stray = []
        for root, dirs, files in os.walk(dist):
            dirs[:] = [d for d in dirs if d != "__pycache__"]          # bytecode of a run from here; never in the zip
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), dist).replace("\\", "/")
                if rel not in listed and rel != "SHA256SUMS":
                    stray.append(rel)
        check(not stray, "no file outside SHA256SUMS%s" % ("" if not stray else ": %s" % sorted(stray)))
    for name in ("MANIFEST.json", "HASHES.txt", "README.md", "TRANSLATORS_NOTES.md", "LICENSE", "NOTICE.txt", "VERSION",
                 "apply_patch.py", "verify_dist.py"):
        check(os.path.exists(os.path.join(dist, name)), "bundle has %s" % name)
    extras = man.get("bundle") or {}
    if extras.get("changelog"):
        check(os.path.exists(os.path.join(dist, "CHANGELOG.md")), "bundle has CHANGELOG.md")
        if os.path.exists(os.path.join(dist, "CHANGELOG.md")) and not man.get("dev_build"):
            with open(os.path.join(dist, "CHANGELOG.md"), encoding="utf-8", errors="replace") as f:
                check(("## [%s]" % man["version"]) in f.read(), "CHANGELOG.md has a section for %s" % man["version"])
    for name in extras.get("licenses") or []:
        check(os.path.exists(os.path.join(dist, "LICENSES", name)), "bundle has LICENSES/%s" % name)
    vf = os.path.join(dist, "VERSION")
    if os.path.exists(vf):
        with open(vf, encoding="utf-8") as f:
            check(f.read().strip() == man["version"], "VERSION file equals the manifest version %s" % man["version"])
    notes = os.path.join(dist, "TRANSLATORS_NOTES.md")
    if os.path.exists(notes):
        with open(notes, encoding="utf-8", errors="replace") as f:
            ph = "PLACEHOLDER" in f.read()
        if man.get("dev_build"):
            check(True, "TRANSLATORS_NOTES.md%s (development bundle)" % (" is still a PLACEHOLDER" if ph else ""))
        else:
            check(not ph, "TRANSLATORS_NOTES.md is not a PLACEHOLDER")
    patches = []
    for n in sorted(man["tracks"], key=int):
        p = man["tracks"][n].get("patch")
        if p:
            patches.append(p)
    if man["volume_iso"].get("patch"):
        patches.append(man["volume_iso"]["patch"])
    for p in patches:
        path = os.path.join(dist, p["file"])
        ok = os.path.exists(path) and os.path.getsize(path) == p["size"] and hash_file(path)[1] == p["sha1"]
        check(ok, "patch %s: size %d, SHA-1 matches the manifest" % (p["file"], p["size"]))
        with open(path, "rb") as f:
            head = f.read(4)
        check(head == b"\xd6\xc3\xc4\x00", "patch %s is a VCDIFF file (magic D6 C3 C4 00)" % p["file"])
    with open(os.path.join(dist, "apply_patch.py"), encoding="utf-8") as f:
        text = f.read()
    tree = ast.parse(text, feature_version=(3, 8))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    embedded = {"discformat", "vcdiff", "bincue2iso"}
    check("@@EMBED" in text and "_EMBEDDED" in text, "apply_patch.py is a single file (modules embedded)")
    check(mods - embedded <= STDLIB_OK | {"importlib"}, "apply_patch.py imports only the standard library%s" % (
        "" if mods - embedded <= STDLIB_OK | {"importlib"} else ": " + ", ".join(sorted(mods - embedded - STDLIB_OK))))
    with open(os.path.join(dist, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    check(all(man["tracks"][n]["source"]["sha1"] in readme for n in man["tracks"]) and man["volume_iso"]["source"]["sha1"] in readme,
          "README.md lists the expected SHA-1 of every source file")
    rc, out = run_apply(dist, os.path.join(dist, "MANIFEST.json"), "--verify")
    check(rc == 1 and "ERROR" in out, "apply_patch.py refuses a non-disc file with a message")


# ----------------------------------------------------------------------------- 2. the player runs
def result_files(man, out_dir, sheet, kind):
    """{n: path} of the output tracks of a cue/gdi run."""
    names = {n: man["tracks"][n]["redump_name" if kind == "cue" else "gdi_name"] for n in man["tracks"]}
    return {int(n): os.path.join(out_dir, names[n]) for n in names}


def check_tracks(man, files, label, built=None):
    ok = True
    for n in sorted(files):
        e = man["tracks"][str(n)]
        p = files[n]
        good = os.path.exists(p) and same(hash_file(p), e["result"])
        ok &= good
        check(good, "%s: track %d has the hash the release promises" % (label, n))
        if built and n in built:
            check(os.path.exists(p) and filecmp.cmp(p, built[n], shallow=False), "%s: track %d byte-equal to the built disc" % (label, n))
    return ok


def player_runs(dist, man, source_cue, scratch, built_disc, ap):
    df = ap.DF
    src = df.open_disc(source_cue, len(man["tracks"]))
    built = None
    if built_disc:
        bd = df.open_disc(built_disc, len(man["tracks"]))
        built = bd.tracks if bd.kind != "iso" else None
    layout = man["layout"]["tracks"]
    st0 = {n: (os.stat(p).st_mtime_ns, os.stat(p).st_size) for n, p in src.tracks.items()}
    # --- cue
    d = os.path.join(scratch, "cue_in")
    for n, p in src.tracks.items():
        link_or_copy(p, os.path.join(d, os.path.basename(p)))
    sheet = os.path.join(d, os.path.basename(source_cue))
    shutil.copyfile(source_cue, sheet)
    rc, text = run_apply(dist, sheet, "--verify")
    check(rc == 0 and "unpatched" in text, "BIN/CUE: --verify says original")
    for label, extra in (("cue", []), ("cue-iso", ["--method", "iso"])):
        out = os.path.join(scratch, label + "_out")
        rc, text = run_apply(dist, sheet, "--out", out, *extra)
        check(rc == 0, "%s: apply_patch.py exit 0" % label)
        files = result_files(man, out, sheet, "cue")
        # the output keeps the names written in the cue
        files = {n: os.path.join(out, os.path.basename(src.tracks[n])) for n in src.tracks}
        check_tracks(man, files, label, built)
        check(open(os.path.join(out, os.path.basename(sheet)), "rb").read() == open(sheet, "rb").read(), "%s: .cue copied unchanged" % label)
        rc, text = run_apply(dist, os.path.join(out, os.path.basename(sheet)), "--verify")
        check(rc == 0 and "already patched" in text, "%s: --verify on the result says already patched" % label)
        shutil.rmtree(out)
    out = os.path.join(scratch, "cue_toiso.iso")
    rc, text = run_apply(dist, sheet, "--to", "iso", "--out", out)
    check(rc == 0 and os.path.exists(out) and same(hash_file(out), man["volume_iso"]["result"]), "cue --to iso: the ISO has the promised hash")
    os.remove(out)
    check(all((os.stat(p).st_mtime_ns, os.stat(p).st_size) == st0[n] for n, p in src.tracks.items()), "BIN/CUE: the source tracks are untouched")
    # --- gdi (synthetic: same tracks renamed, geometry from the manifest)
    g = os.path.join(scratch, "gdi_in")
    lines = [str(len(layout))]
    for n in sorted(layout, key=int):
        name = man["tracks"][n]["gdi_name"]
        link_or_copy(src.tracks[int(n)], os.path.join(g, name))
        lines.append('%s %d %d 2352 %s 0' % (n, layout[n]["lba"], 4 if layout[n]["kind"] == "data" else 0, name))
    gdi = os.path.join(g, "disc.gdi")
    with open(gdi, "w", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    for label, extra in (("gdi", []), ("gdi-iso", ["--method", "iso"])):
        out = os.path.join(scratch, label + "_out")
        rc, text = run_apply(dist, gdi, "--out", out, *extra)
        check(rc == 0, "%s: apply_patch.py exit 0" % label)
        files = {int(n): os.path.join(out, man["tracks"][n]["gdi_name"]) for n in man["tracks"]}
        check_tracks(man, files, label, built)
        check(open(os.path.join(out, "disc.gdi"), "rb").read() == open(gdi, "rb").read(), "%s: .gdi copied unchanged" % label)
        shutil.rmtree(out)
    shutil.rmtree(g)
    shutil.rmtree(d)
    # --- volume iso (made here from the source with the same code the patcher uses)
    iso = os.path.join(scratch, "iso_in", "game.iso")
    os.makedirs(os.path.dirname(iso))
    tracks = [ap.BC.Track(int(n), layout[n]["kind"], src.tracks[int(n)], layout[n]["lba"], 2352) for n in sorted(layout, key=int)]
    ap.BC.write_volume(tracks, iso, False, man["layout"]["hd_base"])
    check(same(hash_file(iso), man["volume_iso"]["source"]), "the volume ISO made from the source has the recorded hash")
    rc, text = run_apply(dist, iso, "--verify")
    check(rc == 0 and "unpatched" in text, "iso: --verify says original")
    out = os.path.join(scratch, "iso_out.iso")
    rc, text = run_apply(dist, iso, "--out", out)
    check(rc == 0 and os.path.exists(out) and same(hash_file(out), man["volume_iso"]["result"]), "iso: the patched ISO has the promised hash")
    if built_disc:
        bd = df.open_disc(built_disc, len(man["tracks"]))
        bi = os.path.join(scratch, "built.iso")
        tr = [ap.BC.Track(int(n), layout[n]["kind"], bd.tracks[int(n)], layout[n]["lba"], 2352) for n in sorted(layout, key=int)]
        ap.BC.write_volume(tr, bi, False, man["layout"]["hd_base"])
        check(filecmp.cmp(out, bi, shallow=False), "iso: the patched ISO is byte-equal to the built disc exported to a volume ISO")
        os.remove(bi)
    rc, text = run_apply(dist, out, "--verify")
    check(rc == 0 and "already patched" in text, "iso: --verify on the result says already patched")
    shutil.rmtree(os.path.dirname(iso))
    os.remove(out)


def main():
    ap_ = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap_.add_argument("--dist", default=None, help="the release folder (default: the folder of this file)")
    ap_.add_argument("--source", help="a .cue of the ORIGINAL disc: patch it in every supported form")
    ap_.add_argument("--disc", action="append", default=[], help="a disc to patch as it is (.cue/.gdi/.iso), repeatable")
    ap_.add_argument("--built", help="the disc (.gdi/.cue) the release was made from: compare the results byte for byte")
    ap_.add_argument("--scratch", default=os.path.join(HERE, "verify_scratch"))
    a = ap_.parse_args()
    dist = os.path.abspath(a.dist or HERE)
    with open(os.path.join(dist, "MANIFEST.json"), encoding="utf-8") as f:
        man = json.load(f)
    log("verifying %s %s in %s" % (man["project"], man["version"], dist))
    check_folder(dist, man)
    scratch = os.path.abspath(a.scratch)
    if a.source or a.disc:
        shutil.rmtree(scratch, ignore_errors=True)
        os.makedirs(scratch)
        ap = load_py(os.path.join(dist, "apply_patch.py"), "apply_patch_shipped")
        try:
            if a.source:
                player_runs(dist, man, os.path.abspath(a.source), scratch, a.built and os.path.abspath(a.built), ap)
            for i, d in enumerate(a.disc):
                out = os.path.join(scratch, "disc%d_out" % i)
                rc, text = run_apply(dist, os.path.abspath(d), "--out", out + (".iso" if d.lower().endswith(".iso") else ""))
                check(rc == 0, "%s: apply_patch.py exit 0" % d)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    log("RESULT: %s" % ("all checks passed" if not FAILS else "%d FAILED: %s" % (len(FAILS), FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
