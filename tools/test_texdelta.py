# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Self-test of tools/texdelta.py (texture deltas, docs/texture-delta.md).   Run:  python -I -X utf8 tools/test_texdelta.py [--full]

 1  encode_delta / decode_delta round trips on random fixtures (equal, edits, shift, growth, shrink, empty source/target,
    zero fill), plain and LZMA-secondary; unchanged regions are COPY (no original bytes stored), the delta stays small.
 2  the legal property: no ADD/RUN instruction stores a run of original bytes of MIN_FAR or more (any offset).
 3  xdelta3 cross-check (skipped with a note without xdelta3): both flavours applied with `xdelta3 -d -s`.
 4  synthetic disc: a raw TBD container and a plain PVR file below a temporary extracted/, repaints below a temporary
    translation/textures -> make -> MANIFEST.tsv -> apply_all gives byte-identical files; verify() agrees.
 5  failures are reported by name, never silently: a different original (other disc revision), a damaged delta, a
    manifest hash that does not match the result, a missing container, a missing delta.
 6  tools/build_patch.py --textures-delta: refused together with --textures-dir, refused (exit 1, texture named) on a
    mismatching original, default (flag absent) is None.
 7  real tree (when extracted/ and translation/textures exist): 12 sampled repaints round-trip; --full: all of them
    (about 30 s).
Writes only below build/test_texdelta/.  Never touches translation/.
"""
import io
import os
import random
import shutil
import struct
import subprocess
import sys
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import texdelta as T       # noqa: E402
import texinject           # noqa: E402
import vcdiff as V         # noqa: E402

WORK = os.path.join(ROOT, 'build', 'test_texdelta')
RESULTS = []


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    print(('PASS ' if cond else 'FAIL ') + msg, flush=True)
    if not cond:
        raise AssertionError(msg)


def raises(fn, exc=Exception):
    try:
        fn()
    except exc as e:
        return str(e)
    return None


def rnd(rng, n):
    return rng.randbytes(n)


def longest_original_run_in_adds(delta, src):
    idx = T.gram_index(src)
    best = 0
    for kind, v in T.delta_pieces(delta):
        if kind == 'add':
            best = max(best, T.longest_common_run(v, src, idx, cap=1000))
    return best


# ------------------------------------------------------------------ 1, 2
def t_codec():
    rng = random.Random(7)
    src = rnd(rng, 40000)
    cases = {}
    cases['equal'] = src
    t = bytearray(src)
    for _ in range(30):
        t[rng.randrange(len(t))] ^= 0x5a
    t[10000:10400] = rnd(rng, 400)
    cases['edits'] = bytes(t)
    cases['shift'] = src[:20000] + b'INSERTED-BYTES' + src[20000:]
    cases['growth'] = src + rnd(rng, 3000)
    cases['shrink'] = src[:11111]
    cases['zero_fill'] = src[:5000] + bytes(9000) + src[14000:]
    cases['moved_block'] = src[:1000] + src[30000:34000] + src[5000:30000] + src[1000:5000] + src[34000:]
    cases['all_new'] = rnd(rng, 40000)
    for name, tgt in sorted(cases.items()):
        for sec in (False, True):
            d = T.encode_delta(src, tgt, sec)
            check(T.decode_delta(d, src) == tgt, 'round trip %-11s secondary=%s (%d -> %d bytes)' % (name, sec, len(tgt), len(d)))
            if name != 'all_new':
                run = longest_original_run_in_adds(d, src)
                check(run < T.MIN_FAR, '  %s: longest original run stored as ADD = %d (< %d)' % (name, run, T.MIN_FAR))
    check(len(T.encode_delta(src, cases['equal'])) < 40, 'equal target = one COPY, a few bytes')
    check(len(T.encode_delta(src, cases['edits'])) < 400 * 2 + 30 * 8 + 120, 'edits: delta is about the changed bytes, not the 40000')
    check(len(T.encode_delta(src, cases['shift'])) < 80, 'shifted insertion: far COPY finds the moved half')
    check(len(T.encode_delta(src, cases['moved_block'])) < 120, 'moved blocks: COPY from other offsets')
    check(len(T.encode_delta(src, cases['zero_fill'])) < 60, 'zero fill is a RUN')
    # degenerate sizes
    for s, g in ((b'', b''), (b'', b'abc'), (b'abc', b''), (b'a', b'a'), (b'abcdefghij', b'abcdefghiX'), (b'x' * 5, b'x' * 3)):
        for sec in (False, True):
            check(T.decode_delta(T.encode_delta(s, g, sec), s) == g, 'tiny round trip %r -> %r secondary=%s' % (s, g, sec))
    # property test against random edits
    for k in range(25):
        s = rnd(rng, rng.randrange(50, 3000))
        t = bytearray(s)
        for _ in range(rng.randrange(1, 6)):
            a = rng.randrange(len(t))
            t[a:a + rng.randrange(0, 60)] = rnd(rng, rng.randrange(0, 60))
        t = bytes(t)
        d = T.encode_delta(s, t, k % 2 == 0)
        assert T.decode_delta(d, s) == t, 'property round trip %d' % k
        assert longest_original_run_in_adds(d, s) < T.MIN_FAR, 'property run %d' % k
    check(True, 'property test: 25 random edit sets round-trip and store no original run >= %d' % T.MIN_FAR)
    return cases, src


# ------------------------------------------------------------------ 3
def t_xdelta3(cases, src):
    import shutil as sh
    xd = sh.which('xdelta3') or (r'C:\ProgramData\chocolatey\bin\xdelta3.exe' if os.path.exists(r'C:\ProgramData\chocolatey\bin\xdelta3.exe') else None)
    if not xd:
        print('SKIP xdelta3 not found; cross-check skipped')
        return
    d = os.path.join(WORK, 'xd')
    os.makedirs(d, exist_ok=True)
    sp, dp, op = (os.path.join(d, n) for n in ('s', 'd', 'o'))
    with open(sp, 'wb') as f:
        f.write(src)
    for name in ('edits', 'shift', 'moved_block', 'growth'):
        for sec in (False, True):
            with open(dp, 'wb') as f:
                f.write(T.encode_delta(src, cases[name], sec))
            if os.path.exists(op):
                os.remove(op)
            r = subprocess.run([xd, '-d', '-s', sp, dp, op], capture_output=True)
            ok = r.returncode == 0 and open(op, 'rb').read() == cases[name]
            check(ok, 'xdelta3 -d applies our %s delta (secondary=%s) %s' % (name, sec, '' if ok else r.stderr[:100]))


# ------------------------------------------------------------------ 4, 5, 6: synthetic disc
def synth_pvr(rng, fmt, dt, w, h, gbix):
    n, exact = texinject.payload_size(fmt, dt, w, h)
    return texinject.build_pvr(fmt, dt, w, h, rnd(rng, n), gbix)


def synth_tbd(recs):
    """raw (uncompressed) TBD bundle from [(fmt, dt, w, h, stamp, payload)]"""
    out = struct.pack('<I', len(recs))
    off = 4 + 16 * len(recs)
    body = b''
    for fmt, dt, w, h, stamp, pl in recs:
        out += struct.pack('<IHHII', fmt | dt << 8, w, h, off + len(body), stamp)
        body += pl
    return out + body


def repaint(rng, pvr_bytes, spots=3):
    p = texinject.parse_pvr(pvr_bytes)
    pl = bytearray(p.payload)
    for _ in range(spots):
        a = rng.randrange(0, max(1, len(pl) - 40))
        pl[a:a + 36] = rnd(rng, 36)
    return texinject.build_pvr(p.fmt, p.dt, p.w, p.h, bytes(pl), p.index)


def build_world():
    rng = random.Random(11)
    base = os.path.join(WORK, 'world')
    shutil.rmtree(base, ignore_errors=True)
    ext, tex = os.path.join(base, 'extracted'), os.path.join(base, 'textures')
    os.makedirs(os.path.join(ext, 'DATA'))
    os.makedirs(os.path.join(ext, 'DPTEX'))
    p1 = rnd(rng, texinject.payload_size(2, 1, 32, 32)[0])
    p2 = rnd(rng, texinject.payload_size(2, 1, 16, 16)[0])
    with open(os.path.join(ext, 'DATA', 'T.TBD'), 'wb') as f:
        f.write(synth_tbd([(2, 1, 32, 32, 0x1111, p1), (2, 1, 16, 16, 0x2222, p2)]))
    plain = synth_pvr(rng, 1, 1, 64, 64, 77)
    with open(os.path.join(ext, 'DPTEX', 'X.PVR'), 'wb') as f:
        f.write(plain)
    orig_tbd1 = texinject.extract_pvr(open(os.path.join(ext, 'DATA', 'T.TBD'), 'rb').read(), '#1')
    paint = {'DATA/T.TBD/#1.pvr': repaint(rng, orig_tbd1), 'DPTEX/X.PVR/@file.pvr': repaint(rng, plain, 4)}
    for rel, b in paint.items():
        p = os.path.join(tex, *rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(b)
    return base, ext, tex, paint


def t_world():
    base, ext, tex, paint = build_world()
    ddir, pdir = os.path.join(base, 'delta'), os.path.join(base, 'pvr')
    rows = T.make(tex, ext, ddir)
    check(sorted(r[0] for r in rows) == sorted(paint), 'make: one row per repainted texture')
    check(os.path.isfile(os.path.join(ddir, 'DATA', 'T.TBD', '#1.vcdiff')) and os.path.isfile(os.path.join(ddir, 'DPTEX', 'X.PVR', '@file.vcdiff')),
          'make: l10n/textures/<same relative path>.vcdiff')
    man = T.read_manifest(os.path.join(ddir, T.MANIFEST))
    check(len(man) == 2 and all(len(r[1]) == 64 and len(r[2]) == 64 and r[3] > 0 for r in man), 'MANIFEST.tsv: path, sha256, sha256, delta size')
    for rel, b in paint.items():
        row = [r for r in man if r[0] == rel][0]
        check(row[1] == T.sha256(b), 'manifest repaint sha256 of %s' % rel)
        check(row[3] == os.path.getsize(os.path.join(ddir, *rel[:-4].split('/')) + '.vcdiff'), 'manifest delta size of %s' % rel)
    done, problems = T.apply_all(ddir, ext, pdir)
    check(not problems and sorted(done) == sorted(paint), 'apply_all: no problems')
    for rel, b in paint.items():
        check(open(os.path.join(pdir, *rel.split('/')), 'rb').read() == b, 'apply_all: %s byte-identical' % rel)
    n, problems = T.verify(tex, ext, os.path.join(base, 'verify'))
    check(n == 2 and not problems, 'verify: 2 textures round-tripped')
    s = T.stats(ddir)
    check(s['count'] == 2 and s['total'] == s['on_disk'], 'stats: count and total')
    res = T.analyze(ddir, ext)
    check(len(res) == 2 and all(r['longest'] < T.MIN_FAR for r in res), 'analyze: no original run >= %d in any ADD' % T.MIN_FAR)
    # CLI apply (single file)
    cont = open(os.path.join(ext, 'DATA', 'T.TBD'), 'rb').read()
    o = os.path.join(base, 'orig1.pvr')
    open(o, 'wb').write(texinject.extract_pvr(cont, '#1'))
    out = os.path.join(base, 'cli_out.pvr')
    with contextlib.redirect_stdout(io.StringIO()):
        rc = T.main(['apply', os.path.join(ddir, 'DATA', 'T.TBD', '#1.vcdiff'), o, out])
    check(rc == 0 and open(out, 'rb').read() == paint['DATA/T.TBD/#1.pvr'], 'CLI apply writes the repaint')

    # ---- 5: failures are named
    def damaged_world(name, mutate_ext=None, mutate_delta=None, mutate_manifest=None):
        w = os.path.join(base, name)
        shutil.rmtree(w, ignore_errors=True)
        shutil.copytree(ext, os.path.join(w, 'extracted'))
        shutil.copytree(ddir, os.path.join(w, 'delta'))
        if mutate_ext:
            mutate_ext(os.path.join(w, 'extracted'))
        if mutate_delta:
            mutate_delta(os.path.join(w, 'delta'))
        if mutate_manifest:
            mutate_manifest(os.path.join(w, 'delta', T.MANIFEST))
        return T.apply_all(os.path.join(w, 'delta'), os.path.join(w, 'extracted'), os.path.join(w, 'pvr'))

    def other_revision(e):
        p = os.path.join(e, 'DATA', 'T.TBD')
        b = bytearray(open(p, 'rb').read())
        b[-1] ^= 0xff                                  # last byte of record #1's payload
        open(p, 'wb').write(bytes(b))
    done2, pr = damaged_world('w_rev', mutate_ext=other_revision)
    check(len(pr) == 1 and pr[0].startswith('DATA/T.TBD/#1.pvr') and 'original texture differs' in pr[0] and 'DPTEX/X.PVR/@file.pvr' in done2,
          'other disc revision: that texture named, the other one still applied (%s)' % pr[:1])

    def bad_delta(d):
        p = os.path.join(d, 'DPTEX', 'X.PVR', '@file.vcdiff')
        b = bytearray(open(p, 'rb').read())
        b[-3] ^= 0x01                                  # flips an address byte or an ADD byte
        open(p, 'wb').write(bytes(b))
    done2, pr = damaged_world('w_delta', mutate_delta=bad_delta)
    check(len(pr) == 1 and pr[0].startswith('DPTEX/X.PVR/@file.pvr'), 'damaged delta: reported by name (%s)' % pr[:1])

    def bad_manifest(p):
        s = open(p, encoding='utf-8').read()
        line = [x for x in s.split('\n') if x.startswith('DATA/T.TBD/#1.pvr')][0]
        parts = line.split('\t')
        parts[1] = '0' * 64
        open(p, 'w', encoding='utf-8', newline='\n').write(s.replace(line, '\t'.join(parts)))
    done2, pr = damaged_world('w_man', mutate_manifest=bad_manifest)
    check(len(pr) == 1 and 'differs from the shipped repaint' in pr[0], 'manifest repaint hash mismatch is reported (%s)' % pr[:1])
    done2, pr = damaged_world('w_cont', mutate_ext=lambda e: os.remove(os.path.join(e, 'DPTEX', 'X.PVR')))
    check(len(pr) == 1 and 'container file not found' in pr[0], 'missing container is reported (%s)' % pr[:1])
    done2, pr = damaged_world('w_nodelta', mutate_delta=lambda d: os.remove(os.path.join(d, 'DATA', 'T.TBD', '#1.vcdiff')))
    check(len(pr) == 1 and pr[0].startswith('DATA/T.TBD/#1.pvr'), 'missing delta file is reported (%s)' % pr[:1])
    with contextlib.redirect_stdout(io.StringIO()):
        rc = T.main(['apply-all', '--delta-dir', os.path.join(base, 'w_rev', 'delta'), '--extracted', os.path.join(base, 'w_rev', 'extracted'),
                     '--out', os.path.join(base, 'w_rev', 'pvr2')])
    check(rc == 1, 'apply-all exits 1 when anything mismatched')
    check(raises(lambda: T.read_manifest(os.path.join(base, 'delta', 'nothing.tsv')), OSError) is not None, 'missing manifest raises')

    # ---- 5b: skeptic regressions (hostile / damaged input, atomic writes, stale files)
    check('DPTEX/X.PVR/@file.pvr: DPTEX/X.PVR/@file.pvr' not in ' '.join(pr) and
          not any(x.count('DATA/T.TBD/#1.pvr') > 1 for x in damaged_world('w_rev2', mutate_ext=other_revision)[1]),
          'problem lines name the texture once (no "X: X: ...")')

    def lzma_damage(d):
        p = os.path.join(d, 'DPTEX', 'X.PVR', '@file.vcdiff')
        b = bytearray(open(p, 'rb').read())
        for i in range(len(b) // 2, len(b) // 2 + 40):
            b[i] ^= 0x5a                               # inside a compressed section: the xz decoder raises its own error
        open(p, 'wb').write(bytes(b))
    try:
        done2, pr = damaged_world('w_lz', mutate_delta=lzma_damage)
        check(len(pr) == 1 and pr[0].startswith('DPTEX/X.PVR/@file.pvr'), 'xz-damaged delta: named, no traceback (%s)' % pr[:1])
    except Exception as e:                             # pragma: no cover
        check(False, 'xz-damaged delta raised %s instead of a named problem' % type(e).__name__)
    rng5 = random.Random(5)
    good = open(os.path.join(ddir, 'DPTEX', 'X.PVR', '@file.vcdiff'), 'rb').read()
    srcb = texinject.extract_pvr(open(os.path.join(ext, 'DATA', 'T.TBD'), 'rb').read(), '#1')
    kinds = set()
    for k in range(120):
        b = bytearray(good)
        b[rng5.randrange(len(b))] ^= 1 << rng5.randrange(8)
        if k % 3 == 0:
            b = b[:rng5.randrange(len(b))]
        try:
            T.decode_delta(bytes(b), srcb)
        except T.TexDeltaError:
            kinds.add('ours')
        except Exception as e:                         # anything else would crash apply_all
            kinds.add(type(e).__name__)
    check(kinds <= {'ours'}, 'decode_delta: 120 damaged deltas raise only TexDeltaError (%s)' % sorted(kinds))
    for evil in ('../escape.pvr', '/abs.pvr', 'A/../../x.pvr', 'A\\B.pvr', 'C:/x.pvr', 'A//B.pvr', 'A/x.txt'):
        check(raises(lambda: T.safe_rel(evil), T.TexDeltaError) is not None, 'manifest path refused: %r' % evil)

    def evil_manifest(p):
        s = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
        last = s[-1].split('\t')
        open(p, 'a', encoding='utf-8', newline='\n').write('\n' + '\t'.join(['../../escape.pvr'] + last[1:]) + '\n')
    w = os.path.join(base, 'w_evil')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(ddir, os.path.join(w, 'delta'))
    evil_manifest(os.path.join(w, 'delta', T.MANIFEST))
    msg = raises(lambda: T.apply_all(os.path.join(w, 'delta'), ext, os.path.join(w, 'out', 'sub')), T.TexDeltaError)
    check(msg is not None and not os.path.exists(os.path.join(w, 'escape.pvr')) and not os.path.exists(os.path.join(w, 'out', 'escape.pvr')),
          'a manifest path that leaves the output directory is refused before anything is written')
    # a delta that is not in the manifest is reported, not ignored
    w = os.path.join(base, 'w_stale')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(ddir, os.path.join(w, 'delta'))
    shutil.copy(os.path.join(w, 'delta', 'DATA', 'T.TBD', '#1.vcdiff'), os.path.join(w, 'delta', 'DATA', 'T.TBD', '#9.vcdiff'))
    done2, pr = T.apply_all(os.path.join(w, 'delta'), ext, os.path.join(w, 'out'))
    check(len(pr) == 1 and '#9.vcdiff' in pr[0] and 'not listed' in pr[0], 'unlisted delta file is reported (%s)' % pr[:1])
    # make removes the delta of a texture that no longer exists, and only on success
    T.make(tex, ext, os.path.join(w, 'delta'))
    check(not os.path.exists(os.path.join(w, 'delta', 'DATA', 'T.TBD', '#9.vcdiff')), 'make prunes stale deltas')
    # atomic writes: no temporary files left behind, an existing file is replaced as a whole
    left = [f for dp, dn, fn in os.walk(base) for f in fn if '.tmp' in f]
    check(not left, 'no temporary files left behind (%s)' % left[:2])
    # deterministic: two makes give identical bytes
    a1 = {r[0]: open(os.path.join(ddir, *r[0][:-4].split('/')) + '.vcdiff', 'rb').read() for r in man}
    T.make(tex, ext, os.path.join(base, 'delta2'))
    a2 = {r[0]: open(os.path.join(base, 'delta2', *r[0][:-4].split('/')) + '.vcdiff', 'rb').read() for r in man}
    check(a1 == a2 and open(os.path.join(ddir, T.MANIFEST), 'rb').read() == open(os.path.join(base, 'delta2', T.MANIFEST), 'rb').read(),
          'make is deterministic (deltas and manifest byte-identical)')

    # ---- 6: build_patch flag
    import build_patch
    ap_src = open(os.path.join(HERE, 'build_patch.py'), encoding='utf-8').read()
    check("'--textures-delta'" in ap_src and 'default off' in ap_src, 'build_patch.py has --textures-delta (default off)')
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = build_patch.main(['--dry-run', '--textures-delta', ddir, '--textures-dir', tex])
    check(rc == 1 and 'exclude each other' in err.getvalue(), '--textures-delta with --textures-dir is refused')
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = build_patch.main(['--dry-run', '--textures-delta', os.path.join(base, 'w_rev', 'delta')])
    check(rc == 1 and 'textures-delta' in err.getvalue(), '--textures-delta: problems stop the build with exit 1 (extracted/ of the real disc does not match the synthetic deltas)')


# ------------------------------------------------------------------ 7: real tree
def t_real(full):
    ext, tex = T.DEF_EXTRACTED, T.DEF_TEXTURES
    if not (os.path.isdir(ext) and os.path.isdir(tex)):
        print('SKIP real tree: extracted/ or translation/textures missing')
        return
    allp = [T._rel(p, tex) for p in T._walk(tex, '.pvr')]
    pick = allp if full else allp[::max(1, len(allp) // 12)][:12]
    orig = T.Originals(ext)
    tot = 0
    for rel in pick:
        cont, tid = T.split_container(rel.split('/'), ext)
        src = orig.texture(cont, tid[:-4])
        tgt = open(os.path.join(tex, *rel.split('/')), 'rb').read()
        d = T.encode_delta(src, tgt, True)
        assert T.decode_delta(d, src) == tgt, rel
        assert longest_original_run_in_adds(d, src) < T.MIN_FAR, rel
        tot += len(d)
    check(True, 'real tree: %d repainted textures round-trip, no original run >= %d in any ADD, %d delta bytes' % (len(pick), T.MIN_FAR, tot))


def main():
    full = '--full' in sys.argv
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    cases, src = t_codec()
    t_xdelta3(cases, src)
    t_world()
    t_real(full)
    bad = [m for ok, m in RESULTS if not ok]
    print('%d checks, %d failed' % (len(RESULTS), len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
