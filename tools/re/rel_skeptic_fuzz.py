"""Skeptic fuzz for tools/vcdiff.encode(move=...): random discs with moved runs, edits inside moved runs, duplicated and
zero sectors, shorter and longer targets, windows above 8 MiB.  Every patch is decoded by our decoder and by xdelta3.

usage: python -I -X utf8 tools/re/rel_skeptic_fuzz.py SCRATCH_DIR [TRIALS] [SEED]
"""
import io
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import vcdiff  # noqa: E402

XD = r"C:\ProgramData\chocolatey\bin\xdelta3.exe"


def sector(rng, ss, uo, ul, kind):
    b = bytearray(ss)
    if kind == "zero":
        pass
    elif kind == "rep":
        b[uo:uo + ul] = bytes([rng.randrange(256)]) * ul
    else:
        b[uo:uo + ul] = rng.randbytes(ul)
    # header / ecc part always differs per placement for raw sectors
    for i in range(min(uo, 16)):
        b[i] = rng.randrange(256)
    for i in range(uo + ul, ss):
        b[i] = rng.randrange(256)
    return bytearray(b)


def make_case(rng, ss, uo, ul, nsec):
    src = []
    for i in range(nsec):
        k = rng.choice(["rand"] * 6 + ["zero", "rep"])
        src.append(sector(rng, ss, uo, ul, k))
    tgt = [bytearray(s) for s in src]
    for _ in range(rng.randrange(1, 6)):
        n = len(tgt)
        a = rng.randrange(n)
        b = min(n, a + rng.randrange(1, max(2, n // 6)))
        run = [bytearray(x) for x in tgt[a:b]]
        op = rng.choice(["move", "move", "copy", "edit", "del", "ins"])
        if op == "move":
            del tgt[a:b]
            at = rng.randrange(len(tgt) + 1)
            for j, r in enumerate(run):
                for i in range(min(uo, 16)):
                    r[i] = rng.randrange(256)
                if rng.random() < 0.15:
                    r[uo + rng.randrange(ul)] ^= 0x5A
            tgt[at:at] = run
        elif op == "copy":
            at = rng.randrange(len(tgt) + 1)
            tgt[at:at] = run
        elif op == "edit":
            for r in run:
                if rng.random() < 0.5:
                    r[uo + rng.randrange(ul)] ^= 0x33
        elif op == "del":
            del tgt[a:b]
        else:
            tgt[a:a] = [sector(rng, ss, uo, ul, "rand") for _ in range(rng.randrange(1, 5))]
    if rng.random() < 0.3 and len(tgt) > 3:
        tgt[-1] = tgt[-1][:rng.randrange(1, ss)]          # ragged tail
    return b"".join(bytes(s) for s in src), b"".join(bytes(s) for s in tgt)


def check(scratch, src, tgt, move, tag):
    sp, tp, pp, op = (os.path.join(scratch, n) for n in ("s.bin", "t.bin", "p.xd", "o.bin"))
    open(sp, "wb").write(src)
    open(tp, "wb").write(tgt)
    with open(sp, "rb") as fs, open(tp, "rb") as ft, open(pp, "wb") as fp:
        vcdiff.encode(fs, ft, fp, hashes=False, move=move)
    patch = open(pp, "rb").read()
    with open(sp, "rb") as fs, open(op, "w+b") as fo:
        vcdiff.decode(fs, patch, fo)
    if open(op, "rb").read() != tgt:
        return "OUR decoder differs (%s)" % tag
    if os.path.exists(XD):
        if os.path.exists(op):
            os.remove(op)
        r = subprocess.run([XD, "-d", "-f", "-s", sp, pp, op], capture_output=True)
        if r.returncode != 0 or open(op, "rb").read() != tgt:
            return "xdelta3 differs (%s): %s" % (tag, r.stderr[-200:])
    return None


def main():
    scratch = sys.argv[1]
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(scratch, exist_ok=True)
    rng = random.Random(seed)
    bad = 0
    for t in range(trials):
        raw = rng.random() < 0.5
        ss, uo, ul = (2352, 16, 2048) if raw else (2048, 0, 2048)
        nsec = rng.choice([8, 30, 120, 400])
        if t % 20 == 19:
            nsec = 4200                          # > 8 MiB for raw sectors, window splits
        src, tgt = make_case(rng, ss, uo, ul, nsec)
        for mv in ((ss, uo, ul), None):
            err = check(scratch, src, tgt, mv, "trial %d raw=%s move=%s n=%d" % (t, raw, bool(mv), nsec))
            if err:
                bad += 1
                print("FAIL", err)
    print("trials", trials, "failures", bad)
    for n in ("s.bin", "t.bin", "p.xd", "o.bin"):
        p = os.path.join(scratch, n)
        if os.path.exists(p):
            os.remove(p)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
