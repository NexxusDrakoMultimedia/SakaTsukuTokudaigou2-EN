"""Self-test of tools/vcdiff.py.   Run:  python -I -X utf8 tools/test_vcdiff.py

 1  changed_ranges: brute-force property check on random pairs (every differing byte is covered,
    uncovered bytes are equal, ranges are ordered and merge-gap separated).
 2  round trips (encode -> parse -> decode, in memory) on random fixtures: equal, small edits, growth,
    shrink, empty target, empty source, both empty, insertion (shift), zero-filled runs (RUN), several
    windows (WINDOW lowered), patch size sanity (equal -> one COPY per window, zero runs stay tiny).
 3  files: `vcdiff.py make/apply/roundtrip/info` on the command line.
 4  xdelta3 cross-checks (skipped with a note if xdelta3 is not on PATH): our patch applied with
    `xdelta3 -d -s`; patches written by `xdelta3 -e` with the default, `-S none`, `-S djw`, `-S lzma`
    secondary compression applied with our decoder.
 5  the file parses as Python 3.8 (the player-side patcher runs on 3.8+).
Writes only below build/test_vcdiff/.
"""
import ast
import io
import os
import random
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import vcdiff as V   # noqa: E402

DEFAULT_WIN = V.WINDOW
WORK = os.path.join(ROOT, 'build', 'test_vcdiff')
T0 = time.time()
RESULTS = []


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    log(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        raise AssertionError(msg)


def rnd_bytes(rng, n):
    return bytes(rng.getrandbits(8) for _ in range(n)) if n < 4096 else rng.randbytes(n)


def make_pair(rng, kind, n=300000):
    """(source, target) bytes for a named case."""
    src = bytearray(rnd_bytes(rng, n))
    src[1000:21000] = bytes(20000)                      # zero area
    src = bytes(src)
    if kind == 'equal':
        return src, src
    if kind == 'edits':
        t = bytearray(src)
        for _ in range(40):
            p = rng.randrange(len(t))
            t[p] ^= 0x5a
        t[100000:100300] = rnd_bytes(rng, 300)
        return src, bytes(t)
    if kind == 'growth':
        return src, src + rnd_bytes(rng, 70000)
    if kind == 'shrink':
        return src, src[:n // 3]
    if kind == 'empty_target':
        return src, b''
    if kind == 'empty_source':
        return b'', src[:5000]
    if kind == 'both_empty':
        return b'', b''
    if kind == 'insertion':
        return src, src[:50000] + b'INSERTED-BYTES' + src[50000:]
    if kind == 'zero_fill':
        t = bytearray(src)
        t[40000:140000] = bytes(100000)
        t[200000:200050] = b'\x07' * 50
        return src, bytes(t)
    if kind == 'tail_rewrite':
        t = bytearray(src)
        t[-5000:] = rnd_bytes(rng, 5000)
        return src, bytes(t)
    raise KeyError(kind)


def rt(src, tgt):
    """encode + decode in memory; returns (patch bytes, decoded bytes)."""
    buf = io.BytesIO()
    shas = V.encode(io.BytesIO(src), io.BytesIO(tgt), buf)
    patch = buf.getvalue()
    out = io.BytesIO()
    sha = V.decode(io.BytesIO(src) if src else None, patch, out)
    return patch, out.getvalue(), sha, shas


# ------------------------------------------------------------------ 1
def test_ranges():
    log('--- 1: changed_ranges')
    rng = random.Random(7)
    for trial in range(300):
        n = rng.choice([0, 1, 5, 63, 64, 65, 255, 256, 257, 4095, 4096, 4097, 70000, 140000])
        m = n + rng.choice([0, 0, 0, 3, 100, -1, -50])
        m = max(m, 0)
        src = bytearray(rnd_bytes(rng, n))
        tgt = bytearray(src[:m]) + bytearray(rnd_bytes(rng, max(0, m - n)))
        for _ in range(rng.choice([0, 1, 3, 10, 50])):
            if tgt:
                p = rng.randrange(len(tgt))
                tgt[p] ^= 1 + rng.randrange(255)
        src, tgt = bytes(src), bytes(tgt)
        rs = V.changed_ranges(src, tgt)
        cov = bytearray(len(tgt))
        last = -10 ** 9
        for a, b in rs:
            assert 0 <= a < b <= len(tgt), (a, b)
            assert a - last > V.MERGE_GAP, 'not merged'
            last = b
            for i in range(a, b):
                cov[i] = 1
        common = min(len(src), len(tgt))
        for i in range(len(tgt)):
            if not cov[i]:
                assert i < common and src[i] == tgt[i], 'uncovered differing byte %d' % i
    check(True, 'changed_ranges: 300 random pairs, every difference covered, ranges ordered and merged')


# ------------------------------------------------------------------ 2
def test_roundtrips():
    log('--- 2: round trips')
    rng = random.Random(1234)
    kinds = ['equal', 'edits', 'growth', 'shrink', 'empty_target', 'empty_source', 'both_empty',
             'insertion', 'zero_fill', 'tail_rewrite']
    for win in (DEFAULT_WIN, 1 << 16, 1000):
        old = V.WINDOW
        V.WINDOW = win
        try:
            for k in kinds:
                src, tgt = make_pair(rng, k)
                patch, out, sha, shas = rt(src, tgt)
                check(out == tgt, 'round trip %-12s window=%-8d src=%-7d tgt=%-7d patch=%d' % (
                    k, win, len(src), len(tgt), len(patch)))
                check(sha == shas[1], '  decoder SHA-1 == encoder target SHA-1')
                if k == 'equal' and win == DEFAULT_WIN:
                    check(len(patch) < 30, '  equal files -> tiny patch (%d bytes)' % len(patch))
                if k == 'zero_fill' and win == DEFAULT_WIN:
                    check(len(patch) < 3000, '  100 KB of zeros costs RUN not ADD (%d bytes)' % len(patch))
                if k == 'empty_target':
                    check(patch == V.MAGIC + b'\x00', '  empty target -> header only')
        finally:
            V.WINDOW = old
    # decode with a source that is too short must fail, not produce garbage
    src, tgt = make_pair(rng, 'edits')
    patch, _, _, _ = rt(src, tgt)
    try:
        V.decode(io.BytesIO(src[:1000]), patch, io.BytesIO())
        ok = False
    except ValueError:
        ok = True
    check(ok, 'decoder refuses a source that is too short')
    # the patch is deterministic
    p1 = rt(src, tgt)[0]
    p2 = rt(src, tgt)[0]
    check(p1 == p2, 'patches are deterministic')


# ------------------------------------------------------------------ 3
def test_cli():
    log('--- 3: command line')
    os.makedirs(WORK, exist_ok=True)
    rng = random.Random(99)
    src, tgt = make_pair(rng, 'edits', 2000000)
    sp, tp, pp, op = (os.path.join(WORK, n) for n in ('a.bin', 'b.bin', 'a_b.xdelta', 'out.bin'))
    for p, d in ((sp, src), (tp, tgt)):
        with open(p, 'wb') as f:
            f.write(d)
    py = [sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'vcdiff.py')]
    r = subprocess.run(py + ['make', sp, tp, pp], capture_output=True, text=True)
    check(r.returncode == 0 and os.path.getsize(pp) > 300, 'vcdiff.py make: %s' % r.stdout.strip().splitlines()[-3:])
    r = subprocess.run(py + ['apply', sp, pp, op], capture_output=True, text=True)
    with open(op, 'rb') as f:
        check(r.returncode == 0 and f.read() == tgt, 'vcdiff.py apply reproduces the target')
    r = subprocess.run(py + ['info', pp], capture_output=True, text=True)
    check(r.returncode == 0 and 'windows' in r.stdout, 'vcdiff.py info: ' + r.stdout.splitlines()[0])
    r = subprocess.run(py + ['roundtrip', sp, tp], capture_output=True, text=True)
    check(r.returncode == 0 and 'identical' in r.stdout, 'vcdiff.py roundtrip: identical')
    r = subprocess.run(py + ['apply', sp, pp, sp], capture_output=True, text=True)
    check(r.returncode != 0, 'apply refuses to overwrite its source')
    check('REDUMP' not in open(os.path.join(HERE, 'vcdiff.py'), encoding='utf8').read(),
          'no Redump-specific text left in vcdiff.py')


# ------------------------------------------------------------------ 4
def run_x3(exe, args):
    return subprocess.run([exe] + args, capture_output=True, text=True)


def test_xdelta3():
    exe = shutil.which('xdelta3') or (r'C:\ProgramData\chocolatey\bin\xdelta3.exe'
                                       if os.path.exists(r'C:\ProgramData\chocolatey\bin\xdelta3.exe') else None)
    if not exe:
        log('--- 4: xdelta3 not found, cross-checks SKIPPED')
        return
    log('--- 4: xdelta3 cross-checks (%s)' % exe)
    os.makedirs(WORK, exist_ok=True)
    rng = random.Random(4242)
    for k in ['equal', 'edits', 'growth', 'shrink', 'zero_fill', 'tail_rewrite', 'insertion']:   # (xdelta3 itself refuses an empty output: 'nothing to output')
        src, tgt = make_pair(rng, k, 3000000)
        for win in (DEFAULT_WIN, 1 << 18):
            V.WINDOW = win
            try:
                patch, out, _, _ = rt(src, tgt)
            finally:
                V.WINDOW = DEFAULT_WIN
            sp, pp, op = (os.path.join(WORK, n) for n in ('x_src.bin', 'x_ours.xdelta', 'x_out.bin'))
            with open(sp, 'wb') as f:
                f.write(src)
            with open(pp, 'wb') as f:
                f.write(patch)
            if os.path.exists(op):
                os.remove(op)
            r = run_x3(exe, ['-d', '-f', '-s', sp, pp, op])
            got = open(op, 'rb').read() if os.path.exists(op) else None
            check(r.returncode == 0 and got == tgt,
                  'xdelta3 -d applies OUR patch: %-12s window=%-8d (%d bytes)%s' % (
                      k, win, len(patch), '' if r.returncode == 0 else ' ' + r.stderr.strip()[-120:]))
    # xdelta3-made patches through our decoder
    for k in ['edits', 'growth', 'shrink', 'insertion', 'zero_fill']:
        src, tgt = make_pair(rng, k, 3000000)
        sp, tp = os.path.join(WORK, 'y_src.bin'), os.path.join(WORK, 'y_tgt.bin')
        with open(sp, 'wb') as f:
            f.write(src)
        with open(tp, 'wb') as f:
            f.write(tgt)
        for label, extra in (('default', []), ('-S none', ['-S', 'none']), ('-S djw', ['-S', 'djw']),
                             ('-S lzma', ['-S', 'lzma'])):
            pp = os.path.join(WORK, 'y.xdelta')
            if os.path.exists(pp):
                os.remove(pp)
            r = run_x3(exe, ['-e', '-f'] + extra + ['-s', sp, tp, pp])
            if r.returncode != 0:
                log('  (xdelta3 -e %s not available: %s)' % (label, r.stderr.strip()[-80:]))
                continue
            with open(pp, 'rb') as f:
                xp = f.read()
            info, _ = V.parse(xp)
            out = io.BytesIO()
            V.decode(io.BytesIO(src), xp, out)
            check(out.getvalue() == tgt, 'OUR decoder applies xdelta3 -e (%s) patch: %-9s %d bytes, secondary=%s' % (
                label, k, len(xp), info['secondary']))
    shutil.rmtree(WORK, ignore_errors=True)


# ------------------------------------------------------------------ 3b move-aware encoder
def fake_raw(k, user):
    """a stand-in for a raw Mode 1 sector: 16-byte header that depends on the position, user data, 288 'parity' bytes."""
    import hashlib
    head = b'\x00' + b'\xff' * 10 + b'\x00' + (k + 150).to_bytes(3, 'big') + b'\x01'
    par = b''.join(hashlib.sha256(head + user + bytes([i])).digest() for i in range(9))[:288]
    return head + user + par


def move_case(rng, sector, wrap):
    """(src, tgt, n_moved_clean): 600 sectors; F1 (sectors 100-139) moved to 300-339 untouched, F2 (200-219) moved to 450
    with one edited sector, the vacated places zeroed, 10 sectors appended."""
    users = [rnd_bytes(rng, 2048) for _ in range(600)]
    for k in range(300, 340):
        users[k] = bytes(2048)
    for k in range(450, 480):
        users[k] = bytes(2048)
    src_u = list(users)
    tgt_u = list(users)
    for i in range(40):
        tgt_u[300 + i] = src_u[100 + i]
        tgt_u[100 + i] = bytes(2048)
    for i in range(20):
        tgt_u[450 + i] = src_u[200 + i]
        tgt_u[200 + i] = bytes(2048)
    e = bytearray(tgt_u[450 + 7])
    e[500] ^= 0xff
    e[501] ^= 0x33
    tgt_u[450 + 7] = bytes(e)
    tgt_u += [rnd_bytes(rng, 2048) for _ in range(10)]
    src = b''.join(wrap(k, u) for k, u in enumerate(src_u))
    tgt = b''.join(wrap(k, u) for k, u in enumerate(tgt_u))
    return src, tgt


def test_moves():
    log('--- 3b: move-aware encoder')
    rng = random.Random(99)
    exe = shutil.which('xdelta3') or (r'C:\ProgramData\chocolatey\bin\xdelta3.exe'
                                       if os.path.exists(r'C:\ProgramData\chocolatey\bin\xdelta3.exe') else None)
    os.makedirs(WORK, exist_ok=True)
    cases = (('cooked 2048', 2048, lambda k, u: u, (2048, 0, 2048)),
             ('raw 2352', 2352, fake_raw, (2352, 16, 2048)))
    for label, sector, wrap, mv in cases:
        src, tgt = move_case(rng, sector, wrap)
        for win in (DEFAULT_WIN, 1 << 16):
            V.WINDOW = win
            try:
                sizes = {}
                for name, m in (('positional', None), ('move-aware', mv)):
                    buf = io.BytesIO()
                    V.encode(io.BytesIO(src), io.BytesIO(tgt), buf, move=m)
                    patch = buf.getvalue()
                    out = io.BytesIO()
                    V.decode(io.BytesIO(src), patch, out)
                    check(out.getvalue() == tgt, '%s window=%d %s: decodes to the target' % (label, win, name))
                    sizes[name] = len(patch)
                    if m:
                        st = dict(V.LAST_STATS)
                        pp = os.path.join(WORK, 'mv.xdelta')
                        sp = os.path.join(WORK, 'mv_src.bin')
                        op = os.path.join(WORK, 'mv_out.bin')
                        if exe:
                            with open(pp, 'wb') as f:
                                f.write(patch)
                            with open(sp, 'wb') as f:
                                f.write(src)
                            if os.path.exists(op):
                                os.remove(op)
                            r = run_x3(exe, ['-d', '-f', '-s', sp, pp, op])
                            got = open(op, 'rb').read() if os.path.exists(op) else None
                            check(r.returncode == 0 and got == tgt, '%s window=%d: xdelta3 -d applies the move-aware patch' % (label, win))
            finally:
                V.WINDOW = DEFAULT_WIN
            per = 304 if sector == 2352 else 0           # header + EDC/ECC of every moved raw sector must be added
            bound = 124 * per + 10 * sector + 4000      # moved + vacated sectors (header, parity) and appended sectors are real new data
            check(sizes['move-aware'] < bound and sizes['move-aware'] * 2 < sizes['positional'],
                  '%s window=%d: move-aware patch %d bytes << positional %d (62 moved sectors, 1 edited, 10 appended)' % (
                      label, win, sizes['move-aware'], sizes['positional']))
            check(st['move_sectors'] >= 60 and st['move_regions'] <= 3,
                  '%s window=%d: %d sectors in %d moved regions found' % (label, win, st['move_sectors'], st['move_regions']))
    # a moved run longer than the window is cut into several windows
    V.WINDOW = 1 << 14
    try:
        src, tgt = move_case(rng, 2048, lambda k, u: u)
        buf = io.BytesIO()
        V.encode(io.BytesIO(src), io.BytesIO(tgt), buf, move=(2048, 0, 2048))
        info, wins = V.parse(buf.getvalue())
        check(max(w.tgt_len for w in wins) <= 1 << 14 and len(wins) > 10, 'long moved runs are cut into windows <= WINDOW (%d windows)' % len(wins))
    finally:
        V.WINDOW = DEFAULT_WIN
    # degenerate inputs must not break: empty target / source, no change, all zero
    for s, t in ((b'', b''), (b'', bytes(4096)), (bytes(4096), b''), (bytes(4096), bytes(4096)), (rnd_bytes(rng, 5000), rnd_bytes(rng, 7000))):
        buf = io.BytesIO()
        V.encode(io.BytesIO(s), io.BytesIO(t), buf, move=(2048, 0, 2048))
        out = io.BytesIO()
        V.decode(io.BytesIO(s) if s else None, buf.getvalue(), out)
        check(out.getvalue() == t, 'move=(2048,0,2048) on a degenerate pair (%d -> %d bytes) round trips' % (len(s), len(t)))
    shutil.rmtree(WORK, ignore_errors=True)


# ------------------------------------------------------------------ 5
def test_py38():
    log('--- 5: python 3.8 syntax')
    with open(os.path.join(HERE, 'vcdiff.py'), encoding='utf8') as f:
        ast.parse(f.read(), feature_version=(3, 8))
    check(True, 'vcdiff.py parses as Python 3.8')


def main():
    os.makedirs(WORK, exist_ok=True)
    test_ranges()
    test_roundtrips()
    test_cli()
    test_moves()
    test_xdelta3()
    test_py38()
    ok = sum(1 for c, _ in RESULTS if c)
    log('RESULT: %d checks passed, %d failed' % (ok, len(RESULTS) - ok))
    shutil.rmtree(WORK, ignore_errors=True)
    return 0 if ok == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
