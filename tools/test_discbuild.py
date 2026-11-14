"""Self-test of tools/discbuild.py.   Run:  python -I -X utf8 tools/test_discbuild.py [--quick]
Needs ~3.5 GB free disk in build/dsc_test_legacy (outputs of the intermediate builds are deleted again; the last
one is deleted at the end together with the folder).  --quick skips the full-disc EDC/ECC pass.  --only-dsc runs only the Stage 3 tests (tools/test_discbuild_dsc.py)."""
import os, sys, time, struct, hashlib, random, shutil, multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import discbuild as D
import discbuild_geom as G
import verify_disc as V
from test_discbuild_dsc import dsc_tests
import gdrom

OUT = os.path.join(ROOT, "build", "dsc_test_legacy")   # own folder (never build/out); removed again at the end
T0 = time.time()


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ test 1
def _verify_range(args):
    path, start_lba, first, count = args
    good = zero = bad = 0
    bad_list = []
    z = bytes(D.SS)
    with open(path, "rb") as f:
        f.seek(first * D.SS)
        for i in range(first, first + count):
            raw = f.read(D.SS)
            if raw == z:
                zero += 1            # all-zero filler sectors (no sync): documented, not Mode 1
                continue
            if D.sector_ok(start_lba + i, raw):
                good += 1
            else:
                bad += 1
                if len(bad_list) < 5:
                    bad_list.append(start_lba + i)
    return good, zero, bad, bad_list


def verify_tracks(paths, tracks, workers=None):
    """paths {track: file}; returns {track: (good, zero, bad, bad_list)}"""
    jobs = []
    for t in tracks:
        n = os.path.getsize(paths[t]) // D.SS
        step = 8192
        for first in range(0, n, step):
            jobs.append((t, (paths[t], D.TRACK_LBA[t], first, min(step, n - first))))
    res = {t: [0, 0, 0, []] for t in tracks}
    with mp.Pool(workers or min(16, os.cpu_count() or 4)) as pool:
        for (t, _), r in zip(jobs, pool.imap(_verify_range, [j[1] for j in jobs], chunksize=1)):
            for k in range(3):
                res[t][k] += r[k]
            res[t][3] += r[3]
    return res


def test_ecc_identity(quick):
    src_paths = {t: os.path.join(ROOT, D.BASE % t) for t in D.TRACK_LBA}
    # (a) fast codec == slow reference transcription of ecm, on random + real sectors
    rnd = random.Random(1)
    s = D.Source(ROOT)
    for lba in [45000, 45016, 50000, 100000, 300000, 549149, 3, 2000]:
        raw = s.raw(lba)
        assert D.ref_pq(raw) == raw, lba
    for _ in range(200):
        user = bytes(rnd.getrandbits(8) for _ in range(2048))
        sec = D.encode_sector(rnd.randrange(0, 549000), user)
        assert D.ref_pq(sec) == sec
    s.close()
    log("1a: vectorised ECC == reference ecm algorithm on 208 sectors: OK")
    # (b) every sector of tracks 1,3,5
    tracks = (1, 3, 5)
    res = verify_tracks(src_paths, tracks)
    total = 0
    for t in tracks:
        g, z, b, bl = res[t]
        n = os.path.getsize(src_paths[t]) // D.SS
        log("1b: track %d: %d sectors, %d identical after EDC/ECC regeneration, %d all-zero filler, %d mismatching %s"
            % (t, n, g, z, b, bl))
        assert g + z + b == n
        assert b == 0, "EDC/ECC mismatch on track %d: %s" % (t, bl)
        total += g
    log("1: EDC/ECC regeneration identity over %d data sectors: OK" % total)


# ------------------------------------------------------------------ helpers
def read_all_files(root, name):
    """{path: sha1 of content} using the independent tools/gdrom.py reader."""
    old = gdrom.BASE
    gdrom.BASE = name + " (Track %d).bin" if name else old
    try:
        d = gdrom.Disc(root)
        out = {}
        for p, lba, size in gdrom.walk(d, *gdrom.pvd_root(d)):
            out[p] = hashlib.sha1(d.read(lba, size)).hexdigest()
        for f, *_ in d.tr:
            f.close()
        return out
    finally:
        gdrom.BASE = old


def read_file(root, name, path):
    old = gdrom.BASE
    gdrom.BASE = name + " (Track %d).bin"
    try:
        d = gdrom.Disc(root)
        for p, lba, size in gdrom.walk(d, *gdrom.pvd_root(d)):
            if p == path:
                r = d.read(lba, size)
                for f, *_ in d.tr:
                    f.close()
                return r
    finally:
        gdrom.BASE = old


def rm_build(name):
    for t in range(1, 6):
        p = D.track_path(OUT, name, t)
        if os.path.exists(p):
            os.remove(p)
    for ext in (".cue", ".gdi"):
        if os.path.exists(os.path.join(OUT, name + ext)):
            os.remove(os.path.join(OUT, name + ext))


def check_structure(name, expect_end=None):
    """Test 5: walk the whole filesystem of the output and validate it."""
    s = D.Source(OUT, name)
    pvd, rl, rs, recs = D.read_filesystem(s)
    end = s.end_lba
    if expect_end is not None:
        assert end == expect_end, (end, expect_end)
    # volume size and IP.BIN TOC lead-out
    vs_le, vs_be = struct.unpack_from("<I", pvd, 80)[0], struct.unpack_from(">I", pvd, 84)[0]
    assert vs_le == vs_be == end - D.HD_BASE, (vs_le, vs_be, end - D.HD_BASE)
    ip = s.read(D.HD_BASE, 16 * 2048)
    lo, = struct.unpack_from("<I", ip, 0x290)
    assert lo == (0x41 << 24) | (end + 150), hex(lo)
    # data regions that may hold file data
    regions = [(D.TRACK_LBA[3], D.TRACK_LBA[4]), (D.TRACK_LBA[5] + D.TRACK_PREGAP[5], end)]
    ext = D.used_extents(s, pvd, rl, rs, recs)
    prev_end = 0
    for st, n, lab in ext:
        assert any(a <= st and st + n <= b for a, b in regions), ("extent outside data tracks", st, n, lab)
        assert st >= prev_end, ("overlap", st, n, lab, prev_end)
        prev_end = st + n
    # both-endian directory fields and '.'/'..' of every directory
    n_checked = 0
    dirs = [(rl, rs)] + [(r.lba, r.size) for r in recs if r.isdir]
    for lba, size in dirs:
        data = s.read(lba, size)
        pos = 0
        while pos < len(data):
            l = data[pos]
            if l == 0:
                pos = (pos // 2048 + 1) * 2048
                continue
            a, b = struct.unpack_from("<I", data, pos + 2)[0], struct.unpack_from(">I", data, pos + 6)[0]
            c, d = struct.unpack_from("<I", data, pos + 10)[0], struct.unpack_from(">I", data, pos + 14)[0]
            assert a == b and c == d, ("both-endian mismatch", lba, pos)
            n_checked += 1
            pos += l
    # path table (L and M) must list every directory with the right extent
    pts, = struct.unpack_from("<I", pvd, 132)
    for off, endian in ((140, "<"), (148, ">")):
        pl, = struct.unpack_from(endian + "I", pvd, off)
        pt = s.read(pl, pts)
        got = []
        pos = 0
        while pos < len(pt):
            ln = pt[pos]
            if ln == 0:
                break
            ex, = struct.unpack_from(endian + "I", pt, pos + 2)
            got.append(ex)
            pos += 8 + ln + (ln & 1)
        assert sorted(got) == sorted([rl] + [r.lba for r in recs if r.isdir]), "path table mismatch"
    files = [r for r in recs if not r.isdir]
    s.close()
    return len(files), len(recs) - len(files), n_checked, len(ext)


def tracks_equal(name_a_dir, name_a, name_b_dir, name_b, tracks):
    for t in tracks:
        if D.sha1_file(D.track_path(name_a_dir, name_a, t)) != D.sha1_file(D.track_path(name_b_dir, name_b, t)):
            return False
    return True


# ------------------------------------------------------------------ tests 2-5
def main():
    quick = "--quick" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    if "--only-dsc" in sys.argv:
        dsc_tests(quick)
        log("ALL TESTS PASSED (dsc only)")
        return
    test_ecc_identity(quick)

    orig_hash = {t: D.sha1_file(os.path.join(ROOT, D.BASE % t)) for t in D.TRACK_LBA}
    log("original track sha1:", {t: h[:12] for t, h in orig_hash.items()})
    orig_files = read_all_files(ROOT, None)
    log("original filesystem: %d files read via tools/gdrom.py" % len(orig_files))
    s = D.Source(ROOT)
    pvd, rl, rs, recs = D.read_filesystem(s)
    sizes = {r.path: (r.lba, r.size) for r in recs if not r.isdir}
    s.close()

    # ---- test 2: no-op rebuild
    r = D.build_disc({}, OUT, "t-noop", ROOT)
    for t in D.TRACK_LBA:
        h = D.sha1_file(r["tracks"][t])
        assert h == orig_hash[t], "no-op rebuild differs in track %d" % t
    assert r["sectors_rewritten"] == 0
    log("2: no-op rebuild byte-identical in all 5 tracks (sha1 equal): OK")
    rm_build("t-noop")
    # the cue produced equals the original cue except for the file names
    with open(os.path.join(ROOT, [f for f in os.listdir(ROOT) if f.endswith(".cue")][0]), newline="") as f:
        oc = f.read().replace("\r\n", "\n")
    mine = D.cue_text(D.BASE[:-len(" (Track %d).bin")]).replace("\r\n", "\n")
    assert oc == mine, "generated cue differs from the original cue"
    log("2b: generated cue text == original cue: OK")

    # ---- test 3: in place (equal size, smaller)
    p_eq = "/DP3.INI"
    p_small = "/FLOW_PRG/MEETING.BIN"
    assert p_eq in sizes and p_small in sizes
    rnd = random.Random(7)
    d = gdrom.Disc(ROOT)
    data_eq = d.read(sizes[p_eq][0], sizes[p_eq][1])
    data_small = d.read(*[sizes[p_small][0], sizes[p_small][1]])
    for f, *_ in d.tr:
        f.close()
    new_eq = bytes(rnd.getrandbits(8) for _ in range(len(data_eq)))
    new_small = data_small[:len(data_small) // 2 + 123]
    r = D.build_disc({p_eq: new_eq, p_small: new_small}, OUT, "t-inplace", ROOT)
    assert r["moves"] == [] and r["new_end_lba"] == r["orig_end_lba"]
    got = read_all_files(OUT, "t-inplace")
    assert set(got) == set(orig_files)
    diff = [p for p in got if got[p] != orig_files[p]]
    assert sorted(diff) == sorted([p_eq, p_small]), diff
    assert got[p_eq] == hashlib.sha1(new_eq).hexdigest()
    assert got[p_small] == hashlib.sha1(new_small).hexdigest()
    # extents unchanged, only size field of the smaller one
    s = D.Source(OUT, "t-inplace")
    _, _, _, recs2 = D.read_filesystem(s)
    s.close()
    for rr in recs2:
        if not rr.isdir:
            ol, osz = sizes[rr.path]
            assert rr.lba == ol
            assert rr.size == (len(new_small) if rr.path == p_small else osz)
    for t in (2, 4):
        assert D.sha1_file(r["tracks"][t]) == orig_hash[t]
    log("3: in-place patch (equal size %d B, smaller %d -> %d B): exactly those 2 of %d files changed, "
        "extents unchanged, audio tracks identical: OK" % (len(new_eq), len(data_small), len(new_small), len(got)))
    check_structure("t-inplace", expect_end=r["orig_end_lba"])
    # every rewritten sector is a valid mode-1 sector
    chk = verify_tracks({t: r["tracks"][t] for t in D.TRACK_LBA}, (3,))
    assert chk[3][2] == 0
    rm_build("t-inplace")

    # ---- test 4: relocation (gap) + append beyond end of track 5
    p_big = "/DP3.INI"        # 5619 B -> grows to 3 sectors: relocated into the free area
    p_huge = "/FLOW_PRG/MEETING.BIN"
    new_big = bytes(rnd.getrandbits(8) for _ in range(5619 + 5000))
    huge_n = 7000 * 2048 + 777      # > 6281 free sectors of track 3 -> appended to track 5
    new_huge = hashlib.sha256(b"x").digest() * (huge_n // 32 + 1)
    new_huge = new_huge[:huge_n]
    name = "SakaTsuku2-EN-test"
    rm_build(name)
    t = time.time()
    r = D.build_disc({p_big: new_big, p_huge: new_huge}, OUT, name, ROOT, allow_overflow=True)   # appends past 549150: emulator-only
    log("4: build with relocation took %.1fs; moves=%s new_end=%d (orig %d)" % (time.time() - t, r["moves"], r["new_end_lba"], r["orig_end_lba"]))
    mv = {m[0]: m for m in r["moves"]}
    assert p_big.upper() in mv and p_huge.upper() in mv
    assert mv[p_big.upper()][2] < D.TRACK_LBA[4], "small file should land in the free area of track 3"
    assert mv[p_huge.upper()][2] >= r["orig_end_lba"] or mv[p_huge.upper()][2] >= D.TRACK_LBA[5], "huge file must be in track 5"
    assert r["new_end_lba"] > r["orig_end_lba"]
    got = read_all_files(OUT, name)
    assert set(got) == set(orig_files)
    diff = sorted(p for p in got if got[p] != orig_files[p])
    assert diff == sorted([p_big, p_huge]), diff
    assert got[p_big] == hashlib.sha1(new_big).hexdigest()
    assert got[p_huge] == hashlib.sha1(new_huge).hexdigest()
    log("4: relocated files read back correctly via tools/gdrom.py, all other %d files unchanged: OK" % (len(got) - 2))
    for tt in (2, 4):
        assert D.sha1_file(r["tracks"][tt]) == orig_hash[tt]
    # tracks 1 identical, track 3 differs only in the expected sectors
    assert D.sha1_file(r["tracks"][1]) == orig_hash[1]
    nf, nd, nrec, next = check_structure(name)
    log("5: structure walk of output: %d files, %d dirs, %d dir records both-endian OK, %d extents inside data tracks, "
        "no overlaps, volume size + IP.BIN lead-out + path tables consistent: OK" % (nf, nd, nrec, next))
    if not quick:
        res = verify_tracks(r["tracks"], (1, 3, 5))
        for t in (1, 3, 5):
            g, z, b, bl = res[t]
            log("4/5: output track %d: %d valid mode-1 sectors, %d zero filler, %d invalid" % (t, g, z, b))
            assert b == 0
    # unchanged sectors really are bit-identical: compare track 3 sector by sector, count differences
    a = open(os.path.join(ROOT, D.BASE % 3), "rb")
    b = open(r["tracks"][3], "rb")
    ndiff = 0
    while True:
        x = a.read(D.SS * 4096)
        y = b.read(D.SS * 4096)
        if not x and not y:
            break
        for i in range(0, len(x), D.SS):
            if x[i:i + D.SS] != y[i:i + D.SS]:
                ndiff += 1
    a.close(); b.close()
    log("4: track 3 sectors that differ from the original: %d (rewritten overall: %d incl. appended)" % (ndiff, r["sectors_rewritten"]))
    gd = open(r["gdi"], newline="").read().split("\r\n")
    assert gd[0] == "5" and len(gd) == 7
    sz = {t: os.path.getsize(r["tracks"][t]) // D.SS for t in D.TRACK_LBA}
    for t in (1, 3, 4):
        assert D.TRACK_LBA[t] + sz[t] == D.TRACK_LBA[t + 1], t
    assert D.TRACK_LBA[5] + sz[5] == r["new_end_lba"]
    log("gdi/cue emitted; track LBAs consistent with file sizes: OK")
    shutil.rmtree(OUT, ignore_errors=True)
    dsc_tests(quick)
    log("ALL TESTS PASSED")


if __name__ == "__main__":
    mp.freeze_support()
    main()
