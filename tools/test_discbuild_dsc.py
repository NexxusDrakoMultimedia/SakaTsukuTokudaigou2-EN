"""Tests of the Stage 3 disc tooling (geometry model, verify_disc, capacity guard, dedupe, add file / directory).
Called by tools/test_discbuild.py (dsc_tests); can also run alone:   python -I -X utf8 tools/test_discbuild_dsc.py [--quick]
Builds go to build/dsc_test/<unique name> and are deleted again; the original tracks are only read (track 5 is hard-linked
into the negative-test folder and never written)."""
import hashlib
import os
import random
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import discbuild as D          # noqa: E402
import discbuild_geom as G     # noqa: E402
import verify_disc as V        # noqa: E402

OUT = os.path.join(ROOT, "build", "dsc_test")
T0 = time.time()


def log(*a):
    print("[%6.1fs] dsc:" % (time.time() - T0), *a, flush=True)


def orig_files():
    """{path: (lba, size)} and a reader of the original dump."""
    s = D.Source(ROOT)
    _, _, _, recs = D.read_filesystem(s)
    return s, {r.path.upper(): (r.lba, r.size) for r in recs if not r.isdir}


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc as e:
        return e
    raise AssertionError("expected %s" % exc.__name__)


def rm(path):
    shutil.rmtree(path, ignore_errors=True)


# ------------------------------------------------------------------ geometry
def t_geometry():
    g = G.Geometry.default()
    assert g.gdi_text("X") == D.gdi_text("X")
    assert g.cue_text("X") == D.cue_text("X")
    assert g.check() == [], g.check()
    cue = os.path.join(ROOT, D.BASE[:-len(" (Track %d).bin")] + ".cue")
    gc = G.Geometry.from_cue(cue)
    for n in g.order:
        a, b = g.tracks[n], gc.tracks[n]
        assert (a.kind, a.lba, a.nsec, a.pregap) == (b.kind, b.lba, b.nsec, b.pregap), (a, b)
    assert gc.end_lba == D.HD_END == g.max_lba
    assert gc.hd_regions() == [(45000, 51342), (56890, 549150)], gc.hd_regions()
    assert gc.in_hd_data(45061, 6281) and not gc.in_hd_data(45061, 6282)        # a file cannot cross into the audio track
    assert not gc.in_hd_data(56700) and gc.in_hd_data(56890)                    # nor start in the pregap
    bad = g.with_track5_sectors(492486).check()
    assert len(bad) == 1 and "ceiling" in bad[0] and "1 sectors over" in bad[0], bad
    assert g.track_at(51341).no == 3 and g.track_at(51342).no == 4 and g.track_at(3268) is None
    log("geometry: default == Redump cue, gdi/cue text identical to discbuild, regions, ceiling check: OK")


def t_path_tables():
    s = D.Source(ROOT)
    pvd, rl, rs, recs = D.read_filesystem(s)
    dirs = {"/": rl}
    dirs.update({r.path.upper(): r.lba for r in recs if r.isdir})
    pts = struct.unpack_from("<I", pvd, 132)[0]
    for off, e in ((140, "<"), (148, ">")):
        pl = struct.unpack_from(e + "I", pvd, off)[0]
        assert s.read(pl, pts) == D.path_table(dirs, e)
    s.close()
    log("path tables: regenerating L and M from the directory tree reproduces the original bytes: OK")


# ------------------------------------------------------------------ verify_disc
def t_verify_original(quick):
    rep = V.verify_disc(ROOT, V.ORIG_NAME, sectors="none" if quick else "all")
    assert rep.ok, rep.text()
    f = rep.facts
    assert (f["files"], f["dirs"], f["free_sectors"], f["headroom"], f["alias_groups"], f["stale_free"]) == (
        1215, 21, 6431, 0, 0, 0), f
    log("verify_disc on the original dump (sectors=%s): OK  files=%d dirs=%d free=%d headroom=%d" % (
        "none" if quick else "all", f["files"], f["dirs"], f["free_sectors"], f["headroom"]))


def neg_setup():
    d = os.path.join(OUT, "neg")
    rm(d)
    os.makedirs(d)
    for t in (1, 2, 3, 4):
        shutil.copyfile(os.path.join(ROOT, D.BASE % t), D.track_path(d, "neg", t))
    p5, o5 = D.track_path(d, "neg", 5), os.path.join(ROOT, D.BASE % 5)
    try:
        os.link(o5, p5)           # track 5 is never written by the negative tests
    except OSError:
        shutil.copyfile(o5, p5)
    return d


def write_sheets(d, gdi_mut=None):
    g = G.Geometry.default()
    with open(os.path.join(d, "neg.cue"), "w", newline="") as f:
        f.write(g.cue_text("neg"))
    gd = g.gdi_text("neg")
    if gdi_mut:
        gd = gdi_mut(gd)
    with open(os.path.join(d, "neg.gdi"), "w", newline="") as f:
        f.write(gd)


def t_verify_negative():
    d = neg_setup()
    write_sheets(d)
    p3 = D.track_path(d, "neg", 3)
    pristine = open(p3, "rb").read()

    def restore():
        with open(p3, "wb") as f:
            f.write(pristine)

    def edit(lba, fn):
        with open(p3, "r+b") as f:
            f.seek((lba - 45000) * D.SS)
            raw = f.read(D.SS)
            user = bytearray(raw[16:16 + 2048])
            fn(user)
            f.seek((lba - 45000) * D.SS)
            f.write(D.encode_sector(lba, bytes(user)))

    def run(sectors="none"):
        r = V.verify_disc(d, "neg", sectors=sectors)
        return r

    r = run("auto")
    assert r.ok, r.text()
    log("negative: clean copy of the original passes (geometry from gdi+cue): OK")
    cases = []

    def bad_pvd(u):
        u[80:88] = D._both32(504151)
    cases.append(("PVD volume size", 45016, bad_pvd, "V3 PVD volume space size", "none"))

    def bad_lead(u):
        struct.pack_into("<I", u, 0x290, (0x41 << 24) | 549301)
    cases.append(("IP.BIN lead-out", 45000, bad_lead, "lead-out", "none"))

    def bad_crc(u):
        u[0x20:0x24] = b"0000"
    cases.append(("IP.BIN crc", 45000, bad_crc, "CRC", "none"))

    def bad_toc(u):
        struct.pack_into("<I", u, 0x10c, 0x4100ded1)
    cases.append(("IP.BIN TOC entry", 45000, bad_toc, "TOC track 5", "none"))

    def bad_endian(u):
        u[68 + 6] ^= 1
    cases.append(("both-endian", 45020, bad_endian, "both-endian", "none"))

    def bad_dotdot(u):
        u[34 + 33] = 0
    cases.append(("'..' record", 45020, bad_dotdot, "second record is not '..'", "none"))

    def overlap(u):
        l1 = u[68]
        u[70:78] = u[68 + l1 + 2:68 + l1 + 10]       # first file takes the second file's extent
    cases.append(("overlap", 45020, overlap, "overlap", "none"))

    def outside(u):
        struct.pack_into("<I", u, 70, 51400)
        struct.pack_into(">I", u, 74, 51400)
    cases.append(("extent in the audio track", 45020, outside, "not wholly inside", "none"))

    def beyond(u):
        struct.pack_into("<I", u, 70, 549149)
        struct.pack_into(">I", u, 74, 549149)
        struct.pack_into("<I", u, 78, 8192)
        struct.pack_into(">I", u, 82, 8192)
    cases.append(("extent past the ceiling", 45020, beyond, "past the GD-ROM ceiling", "none"))

    def bad_pt(u):
        u[12] ^= 0x10
    cases.append(("path table L extent", 45018, bad_pt, "path tables", "none"))

    def swap_names(u):
        # two sorted names exchanged -> not sorted
        l1 = u[68]
        l2 = u[68 + l1]
        a, b = bytes(u[68:68 + l1]), bytes(u[68 + l1:68 + l1 + l2])
        u[68:68 + l2 + l1] = b + a
    cases.append(("unsorted records", 45020, swap_names, "sorted", "none"))
    for label, lba, fn, needle, sec in cases:
        edit(lba, fn)
        r = run(sec)
        assert not r.ok and any(needle in e for e in r.errors), (label, r.text())
        restore()
        log("negative: %-26s detected (%s)" % (label, needle))
    # EDC damage in a data sector
    with open(p3, "r+b") as f:
        f.seek((45030 - 45000) * D.SS + 2064)
        f.write(b"\x55\x55\x55\x55")
    r = run("auto")
    assert any("V9" in e and "45030" in e for e in r.errors), r.text()
    restore()
    log("negative: EDC damage detected (V9)")
    # gdi / cue disagreements
    write_sheets(d, lambda t: t.replace("51342 0", "51343 0"))
    r = run("none")
    assert any("G1" in e for e in r.errors), r.text()
    write_sheets(d, lambda t: t.replace('"neg (Track 5).bin"', '"neg (Track 9).bin"'))
    r = run("none")
    assert any("G1" in e for e in r.errors), r.text()
    log("negative: gdi/cue disagreement detected (G1)")
    # a track file that is not whole sectors
    write_sheets(d)
    with open(p3, "ab") as f:
        f.write(b"\0" * 5)
    r = run("none")
    assert any("whole number" in e for e in r.errors), r.text()
    restore()
    r = run("none")
    assert r.ok, r.text()
    rm(d)
    log("negative: verify_disc detected %d classes of damage and passes the restored copy: OK" % (len(cases) + 3))


# ------------------------------------------------------------------ capacity guard
def t_capacity_guard():
    s, files = orig_files()
    hole = 6281
    big = lambda n: bytes(n * 2048)
    pl = D.plan_patches(s, {"/DP3.INI": big(hole)})
    assert pl.new_end == 549150 and pl.moves[0][2] == 45061
    e = raises(D.DiscFull, D.plan_patches, s, {"/DP3.INI": big(hole + 1)})
    assert "disc full" in str(e) and "549150" in str(e) and "6282 sector" in str(e), str(e)
    pl = D.plan_patches(s, {"/DP3.INI": big(hole + 1)}, allow_overflow=True)
    assert pl.new_end == 549150 + hole + 1 and pl.warnings and "OVERFLOW" in pl.warnings[0]
    e = raises(D.DiscFull, D.plan_patches, s, {"/DP3.INI": big(5)}, "append")
    assert "disc full" in str(e)
    # 7 movers of 1000 sectors: the hole holds 6; the 7th needs the space freed by dedupe
    small = [p for p, (l, sz) in sorted(files.items()) if 0 < sz <= 60 * 2048][:7]
    movers = {p: bytes([i + 1]) + bytes(1000 * 2048 - 1) for i, p in enumerate(small)}     # distinct bytes: no dedupe collapse
    e = raises(D.DiscFull, D.plan_patches, s, movers)
    assert "--dedupe-files" in str(e)
    pl = D.plan_patches(s, movers, dedupe=True)
    assert pl.new_end == 549150 and len(pl.moves) == 7 and pl.free_sectors > 0
    assert any(m[2] >= 56890 for m in pl.moves), pl.moves          # the 7th lands in an extent vacated by a duplicate
    s.close()
    log("capacity guard: 6281-sector file fits, 6282 raises DiscFull (message names LBA 549150, the shortfall and "
        "--dedupe-files); allow_overflow warns; 7 x 1000-sector movers only fit with dedupe: OK")


# ------------------------------------------------------------------ helpers for built discs
def read_back(disc_dir, name):
    """{path: sha1} of every file, via the independent Gdfs model (path table lookup, '.' size)."""
    rep, g, disc, vol = V.open_volume(disc_dir, name)
    assert rep.ok and vol is not None, rep.text()
    fs = V.Gdfs(disc, g)
    out = {}
    for p in sorted(vol["files"]):
        h = fs.open(p)
        assert h[:2] == vol["files"][p], (p, h)
        out[p] = hashlib.sha1(fs.read(h)).hexdigest()
    disc.close()
    return out


def orig_hashes():
    s, files = orig_files()
    out = {p: hashlib.sha1(s.read(l, sz)).hexdigest() for p, (l, sz) in files.items()}
    s.close()
    return out


# ------------------------------------------------------------------ dedupe
def t_dedupe():
    s, files = orig_files()
    read = lambda p: s.read(*files[p])
    ohash = {p: hashlib.sha1(read(p)).hexdigest() for p in files}
    # (a) no patches at all: the 15 groups become 15 shared extents, nothing else changes
    plan = D.plan_patches(s, {}, dedupe=True)
    assert len(plan.dedupe) == 15 and sum(len(g[1]) for g in plan.dedupe) == 20
    assert len(plan.over) == 6, sorted(plan.over)            # only directory sectors
    assert not D.plan_patches(s, {}).over                    # default: untouched
    name = "dd-plain"
    r = D.build_disc({}, OUT, name, ROOT, dedupe=True)
    assert r["sectors_rewritten"] == 6 and r["new_end_lba"] == 549150
    rep = V.verify_disc(OUT, name, ROOT, expect={}, rewritten=r["rewritten_lbas"], sectors="auto", read_files=True)
    assert rep.ok, rep.text()
    assert rep.facts["alias_groups"] == 15 and rep.facts["free_sectors"] == 6431 + 3726, rep.facts
    assert rep.facts["diff_sectors"] == 6
    got = read_back(OUT, name)
    assert got == ohash, "a file reads differently through the path-table lookup"
    # the shared names really point to one extent
    rep2, g, disc, vol = V.open_volume(OUT, name)
    al = vol["alias"]
    assert len(al) == 15 and sum(len(v) for v in al.values()) == 35
    disc.close()
    log("dedupe (no patches): 15 groups / 20 extents shared, 6 directory sectors rewritten, verify_disc OK, all %d files read back "
        "by name equal the original, free %d -> %d sectors: OK" % (len(got), 6431, rep.facts["free_sectors"]))
    for t in range(1, 6):
        os.remove(D.track_path(OUT, name, t))
    for ext in (".cue", ".gdi"):
        os.remove(os.path.join(OUT, name + ext))
    # (b) patches: BAR.TBD changed in both copies (stays shared), HELP.DAT in one copy only (group splits),
    #     COMM.BIN family (4 files) grows identically (keeper moves, the 3 followers follow)
    bar = bytearray(read("/ETC_DATA/BAR.TBD"))
    bar[100] ^= 0xFF
    hlp = bytearray(read("/ATFIRST/HELP.DAT"))
    hlp[5] ^= 0xFF
    comm = read("/FLOW_PRG/COMM.BIN") + b"\x01" * 9000
    patches = {"/ETC_DATA/BAR.TBD": bytes(bar), "/ATFIRST/BAR.TBD": bytes(bar), "/ATFIRST/HELP.DAT": bytes(hlp)}
    for n in ("COMM", "CON_REP", "NF_CON", "PASS_PL"):
        patches["/FLOW_PRG/%s.BIN" % n] = comm
    name = "dd-patch"
    r = D.build_disc(patches, OUT, name, ROOT, dedupe=True)
    assert len(r["dedupe"]) == 14, [g[0] for g in r["dedupe"]]
    assert len(r["moves"]) == 1 and r["moves"][0][0] == "/FLOW_PRG/COMM.BIN", r["moves"]     # one move for the 4 names
    rep = V.verify_disc(OUT, name, ROOT, expect=patches, rewritten=r["rewritten_lbas"], sectors="auto")
    assert rep.ok, rep.text()
    got = read_back(OUT, name)
    for p in files:
        want = hashlib.sha1(patches[p]).hexdigest() if p in patches else ohash[p]
        assert got[p] == want, p
    rep2, g, disc, vol = V.open_volume(OUT, name)
    f = vol["files"]
    assert f["/ETC_DATA/BAR.TBD"] == f["/ATFIRST/BAR.TBD"]                                  # still shared, new bytes
    assert f["/ATFIRST/HELP.DAT"][0] != f["/ETC_DATA/HELP.DAT"][0]                         # split: one patched copy
    assert len({f["/FLOW_PRG/%s.BIN" % n] for n in ("COMM", "CON_REP", "NF_CON", "PASS_PL")}) == 1
    assert f["/FLOW_PRG/COMM.BIN"][1] == len(comm) and f["/FLOW_PRG/COMM.BIN"][0] != files["/FLOW_PRG/COMM.BIN"][0]
    disc.close()
    log("dedupe (patched): shared pairs stay shared with new bytes, a one-sided patch un-shares, the grown COMM.BIN family "
        "moves once and its 3 followers follow; verify_disc OK, all files read back by name as expected: OK")
    for t in range(1, 6):
        os.remove(D.track_path(OUT, name, t))
    for ext in (".cue", ".gdi"):
        os.remove(os.path.join(OUT, name + ext))
    s.close()


# ------------------------------------------------------------------ add file / directory
def t_add_errors():
    s, files = orig_files()
    spec = D.DiscSpec()
    raises(D.DiscError, D.add_file, spec, "/bad name.txt", b"x")
    raises(D.DiscError, D.add_file, spec, "/", b"x")
    spec.add_file("/NEW.TXT", b"a")
    raises(D.DiscError, D.add_file, spec, "/new.txt", b"b")
    raises(D.DiscError, D.plan_patches, s, {}, add_files={"/DP3.INI": b"x"})                 # exists: use a patch
    raises(D.DiscError, D.plan_patches, s, {}, add_files={"/DP3.INI/X.TXT": b"x"})           # a file is no directory
    raises(D.DiscError, D.plan_patches, s, {}, add_files={"/EVENT": b"x"})                   # a directory is no file
    raises(KeyError, D.plan_patches, s, {"/NOPE.BIN": b"x"})
    assert not D.plan_patches(s, {}, add_files={}, add_dirs=[]).over                           # empty options = default
    s.close()
    log("add_file / add_directory: bad names, duplicates, file-vs-directory clashes are refused; empty options change nothing: OK")


def t_add_build():
    s, files = orig_files()
    ohash = {p: hashlib.sha1(s.read(*files[p])).hexdigest() for p in files}
    ev = sorted(p for p in files if p.startswith("/EVENT/"))[0]
    wp = sorted(p for p in files if p.startswith("/DPWWW/") and p.count("/") == 2)[0]
    rnd = random.Random(3)
    patches = {}
    for p in ("/DP3.INI", ev, wp):                       # patches into directories that will be rewritten / moved
        data = bytearray(s.read(*files[p]))
        data[3] ^= 0x5A
        patches[p] = bytes(data)
    patches["/DP3.INI"] = patches["/DP3.INI"][:5000]     # shorter: the record size changes inside the rewritten directory
    spec = D.DiscSpec(patches, dedupe=True)
    adds = {"/README.TXT": b"Translator's notes\r\n" * 20, "/EN/NOTE.TXT": bytes(rnd.getrandbits(8) for _ in range(5000)),
            "/EVENT/ZZNOTE1.TXT": b"one", "/EVENT/ZZNOTE2.TXT": b"two"}
    for i in range(40):
        adds["/DPWWW/PAGE%03d.TXT" % i] = b"page %d" % i
    for i in range(100):
        spec.add_directory("/DIRECTORY_%03d" % i)
    for k, v in adds.items():
        spec.add_file(k, v)
    spec.add_file("/EN/DEEP/MORE/X.TXT", b"nested")
    name = "add-all"
    t = time.time()
    r = D.build_disc(spec, OUT, name, ROOT)
    log("add build: %.1fs, moved dirs %s, new dirs %d, added files %d, rewritten sectors %d" % (
        time.time() - t, [d for d, _ in r["moved_dirs"]], len(r["new_dirs"]), len(r["added"]), r["sectors_rewritten"]))
    assert sorted(d for d, _ in r["moved_dirs"]) == ["/", "/DPWWW", "/EVENT"], r["moved_dirs"]
    assert len(r["new_dirs"]) == 100 + 3                                      # 100 + /EN + /EN/DEEP + /EN/DEEP/MORE
    expect = dict(patches)
    expect.update(adds)
    expect["/EN/DEEP/MORE/X.TXT"] = b"nested"
    rep = V.verify_disc(OUT, name, ROOT, expect=expect, rewritten=r["rewritten_lbas"], sectors="auto")
    assert rep.ok, rep.text()
    rep2, g, disc, vol = V.open_volume(OUT, name)
    assert vol["pts"] > 2048, vol["pts"]                                       # path table needs two sectors now
    assert len(vol["dirs"]) == 21 + 103 and len(vol["files"]) == 1215 + len(adds) + 1
    fs = V.Gdfs(disc, g)
    got = {}
    for p in sorted(vol["files"]):
        h = fs.open(p)
        got[p] = fs.read(h)
    disc.close()
    for p in files:
        want = patches.get(p)
        assert (hashlib.sha1(got[p]).hexdigest() == (hashlib.sha1(want).hexdigest() if want is not None else ohash[p])), p
    for p, v in expect.items():
        assert got[p.upper()] == v, p
    # the gdi / cue of the output parse back to the same geometry
    gg = G.Geometry.from_gdi(r["gdi"])
    gc = G.Geometry.from_cue(r["cue"])
    assert [(t.no, t.lba, t.nsec) for t in gg.tracks.values()] == [(t.no, t.lba, t.nsec) for t in gc.tracks.values()]
    log("add build: root, EVENT and DPWWW moved (children '..', parent records, both path tables, PVD root record kept in step), "
        "path table now %d bytes (2 sectors), %d dirs / %d files, every file read back by name: OK" % (
            vol["pts"], len(vol["dirs"]), len(vol["files"])))
    for t in range(1, 6):
        os.remove(D.track_path(OUT, name, t))
    for ext in (".cue", ".gdi"):
        os.remove(os.path.join(OUT, name + ext))
    s.close()


def dsc_tests(quick=False):
    os.makedirs(OUT, exist_ok=True)
    t_geometry()
    t_path_tables()
    t_verify_original(quick)
    t_verify_negative()
    t_capacity_guard()
    t_add_errors()
    t_dedupe()
    t_add_build()
    rm(OUT)
    log("dsc tests: ALL PASSED")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    dsc_tests("--quick" in sys.argv)
