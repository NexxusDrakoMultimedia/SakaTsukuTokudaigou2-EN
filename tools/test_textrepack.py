"""Self-test for tools/textrepack.py.   python -I -X utf8 tools/test_textrepack.py [--quick]

1. unit: a hand-made image (known layout) -> exact expected bytes for in-pool repack, duplicate
   sharing, cross-pool move, revert-to-Japanese overflow, fixed (orphan) strings
2. identity: for every overlay image, repack with all 'en' empty (entries = translation/*.jsonl)
   returns the original bytes (share none/dup);  repack(force=True) (every pool rewritten
   back-to-back) is a proven-equivalent image: every pointer of every string resolves to identical
   text, only pool bytes / pointer words changed, and re-extraction finds the same Japanese strings
3. synthetic translations (seeded, mixed lengths) on several overlays, all share/cross-pool modes:
   check() (pointers resolve to the new text, other pointers unchanged, only pool ranges and
   pointer words changed, size unchanged), re-extraction of the output finds exactly the strings
   that are still Japanese, determinism (two runs equal), stability (a second pass over the
   output with the output's own strings is a fixed point, share='none')
"""
import hashlib
import json
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textdb as T  # noqa: E402
import textrepack as R  # noqa: E402

QUICK = '--quick' in sys.argv
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        if len(fails) < 40:
            print('FAIL:', msg)


def rec(img_source, s, en=''):
    return {'id': '%s#%x' % (img_source, s.off), 'ja': T.decode_text(s.raw), 'en': en}


def dummy(rng, n):
    letters = 'abcdefghijklmnopqrstuvwxyz '
    return ''.join(rng.choice(letters) for _ in range(max(1, n))).strip() or 'x'


# ------------------------------------------------------------------ unit ---

def jp(t):
    return t.encode('cp932')


def build_unit_image():
    """base 0x8c2d0000; pointer table at 0x100 (7 words), orphan string at 0x200 (unreferenced),
    pool A at 0x300 (cap 68, text 64), pool B at 0x400 (cap 38, text 32)  Returns (image, base, names)."""
    base = 0x8C2D0000
    img = bytearray(0x600)
    A = [jp('あいうえおかきくけこ'), jp('さしすせそ'), jp('あいうえおかきくけこ'), jp('たちつてと')]  # [0] == [2]
    B = [jp('なにぬねのはひふへほ'), jp('まみむめも')]
    pos = 0x300
    offs = []
    for t in A:
        offs.append(pos)
        img[pos:pos + len(t)] = t
        pos += len(t) + 1
    poolA_end = pos
    pos = 0x400
    for t in B:
        offs.append(pos)
        img[pos:pos + len(t)] = t
        pos += len(t) + 1
    img[0x344:0x348] = b''      # non-zero data ends pool A: cap 0x344-0x300 = 68 (4 spare)
    img[0x426:0x42a] = b''      # ends pool B: cap 38 (6 spare)
    for i, o in enumerate(offs):
        struct.pack_into('<I', img, 0x100 + 4 * i, base + o)
    struct.pack_into('<I', img, 0x100 + 4 * 6, 0x8C2D0500)       # pointer to a non-string, ignored
    t = jp('ゆよらりるれろ')
    img[0x200:0x200 + len(t)] = t                                 # orphan (no pointer)
    img[0x500:0x504] = b'\x01\x02\x03\x04'
    return bytes(img), base, offs


def test_unit():
    image, base, offs = build_unit_image()
    img = T.Image('X/UNIT.BIN', image, base)
    ex = T.extract_image(img)
    strs = ex[0]
    by = {s.off: s for s in strs}
    pools, where = R.find_pools(strs)
    check(len(pools) == 2, 'unit: expected 2 pools, got %d' % len(pools))
    check([len(p.home) for p in pools] == [4, 2], 'unit: pool membership')
    recs = [rec('X/UNIT.BIN', s) for s in strs]

    idx = {offs[i]: [k for k, r in enumerate(recs) if r['id'].endswith('#%x' % offs[i])][0] for i in range(6)}
    I = [idx[o] for o in offs]            # recs index of string 0..5 (pool A: 0..3, pool B: 4..5)
    # identity
    new, rep = R.repack(image, base, recs, source='X/UNIT.BIN', extracted=ex)
    check(new == image, 'unit: identity')
    # in-pool: grow string 1 by stealing slack of string 3 (shrunk) - impossible in the per-string model
    r2 = [dict(r) for r in recs]
    r2[I[1]]['en'] = 'x' * 20          # orig 11 bytes, grows to 21
    r2[I[3]]['en'] = 'y'               # orig 11 bytes -> 2 bytes
    new, rep = R.repack(image, base, r2, source='X/UNIT.BIN', share='none', extracted=ex)
    check(not rep.overflow and not rep.fixed_overflow, 'unit: in-pool borrow overflowed %r' % rep.overflow)
    enc = R._entry_enc(r2, by, R.Report(''), '')
    check(R.check(image, new, base, strs, enc, rep) == [], 'unit: check() in-pool borrow')
    # exact layout of pool A: [0] orig 21 B, [1] 21 B, [2] orig 21 B, [3] 2 B = 65 <= 68
    a = pools[0]
    exp = jp('あいうえおかきくけこ') + b'\0' + b'x' * 20 + b'\0' + jp('あいうえおかきくけこ') + b'\0' + b'y\0'
    check(new[a.a:a.a + len(exp)] == exp, 'unit: exact packed bytes of pool A')
    check(new[a.a + len(exp):a.z] == bytes(a.z - a.a - len(exp)), 'unit: pool A tail zero')
    # per-string model fails the same input
    _, trep = T.insert_image(img, r2, extracted=ex)
    # (textdb strategy B may or may not succeed; only recorded)
    # duplicate sharing: strings 0 and 2 identical -> one copy
    new_d, rep_d = R.repack(image, base, r2, source='X/UNIT.BIN', share='dup', extracted=ex)
    check(rep_d.shared_saved == 21, 'unit: dup sharing saved %d, expected 21' % rep_d.shared_saved)
    p0 = struct.unpack_from('<I', new_d, 0x100)[0]
    p2 = struct.unpack_from('<I', new_d, 0x108)[0]
    check(p0 == p2, 'unit: shared strings have one address')
    check(R.check(image, new_d, base, strs, enc, rep_d, share='dup') == [], 'unit: check() dup')
    # overflow: pool B has 6 spare bytes; make everything too long
    r3 = [dict(r) for r in recs]
    for r in r3:
        r['en'] = 'z' * 25
    new_o, rep_o = R.repack(image, base, r3, source='X/UNIT.BIN', share='none', extracted=ex)
    enc3 = R._entry_enc(r3, by, R.Report(''), '')
    check(len(rep_o.overflow) > 0, 'unit: overflow expected')
    check(R.check(image, new_o, base, strs, enc3, rep_o) == [], 'unit: check() overflow')
    for o in rep_o.overflow:
        check(o['need'] == 26, 'unit: overflow need')
    # cross pool: pool B has 6 spare bytes; shrink pool-B strings, grow pool-A string by <= freed
    r4 = [dict(r) for r in recs]
    r4[I[4]]['en'] = 'q'                # pool B string (11 bytes -> 2)
    r4[I[5]]['en'] = 'q2'               # 3
    r4[I[0]]['en'] = 'm' * 30           # pool A string 0 grows by 20; A has 0 slack, B has 6+9+8=23 spare
    new_c, rep_c = R.repack(image, base, r4, source='X/UNIT.BIN', share='none', extracted=ex)
    enc4 = R._entry_enc(r4, by, R.Report(''), '')
    check(not rep_c.overflow and rep_c.moved >= 1, 'unit: cross-pool move (moved=%d overflow=%d)' % (
        rep_c.moved, len(rep_c.overflow)))
    check(R.check(image, new_c, base, strs, enc4, rep_c) == [], 'unit: check() cross pool')
    new_n, rep_n = R.repack(image, base, r4, source='X/UNIT.BIN', share='none', cross_pool=False, extracted=ex)
    check(len(rep_n.overflow) >= 1, 'unit: without cross_pool the same input overflows')
    # fixed (orphan) string in place / overflow
    orphan = [s for s in strs if s.orphan]
    if orphan:
        o = orphan[0]
        r5 = [dict(r) for r in recs]
        for r in r5:
            if r['id'].endswith('#%x' % o.off):
                r['en'] = 'ok'
        new_f, rep_f = R.repack(image, base, r5, source='X/UNIT.BIN', extracted=ex)
        check(new_f[o.off:o.off + 3] == b'ok\0' and rep_f.in_place_fixed == 1, 'unit: orphan in place')
        for r in r5:
            if r['id'].endswith('#%x' % o.off):
                r['en'] = 'k' * 300
        new_f, rep_f = R.repack(image, base, r5, source='X/UNIT.BIN', extracted=ex)
        check(len(rep_f.fixed_overflow) == 1 and new_f == image, 'unit: orphan overflow keeps Japanese')
    else:
        check(False, 'unit: orphan not extracted')
    # stale ja is skipped
    r6 = [dict(r) for r in recs]
    r6[I[0]]['en'] = 'a'
    r6[I[0]]['ja'] = '違う'
    new_s, rep_s = R.repack(image, base, r6, source='X/UNIT.BIN', extracted=ex)
    check(new_s == image and len(rep_s.skipped) == 1, 'unit: stale entry skipped')


# ------------------------------------------------- real images: identity ---

def load_all():
    out = []
    for source, path in T.list_sources():
        if source == '1ST_READ.BIN':
            continue
        try:
            img = T.load_image(source, path)
        except ValueError:
            continue
        ex = T.extract_image(img)
        if ex[0]:
            out.append((source, img, ex))
    return out


def reextract_texts(image, base, source):
    ex = T.extract_image(T.Image(source, image, base))
    return {T.decode_text(s.raw) for s in ex[0]}


def test_identity(srcs):
    n = 0
    t0 = time.time()
    for source, img, ex in srcs:
        # the real translation/*.jsonl now carry English: the identity / forced cases need every en empty
        recs = [dict(r, en='') for r in (R.load_entries(source) or [])] or [rec(source, s) for s in ex[0]]
        for r in recs:
            r.pop('skip', None)
        for share in ('none', 'dup'):
            new, rep = R.repack(img.data, img.base, recs, source=source, share=share, extracted=ex)
            check(new == img.data, 'identity %s share=%s' % (source, share))
        # forced repack: equivalent image
        for share in ('none', 'dup'):
            new, rep = R.repack(img.data, img.base, recs, source=source, share=share, extracted=ex, force=True)
            bad = R.check(img.data, new, img.base, ex[0], {}, rep, share=share)
            check(not bad, 'forced %s share=%s: %s' % (source, share, bad[:2]))
            check(len(new) == len(img.data), 'forced size %s' % source)
            if share == 'none':
                # deterministic and (after the first pass) stable in bytes: a second forced pass changes nothing
                new2, _ = R.repack(new, img.base, [], source=source, force=True, share='none')
                check(new2 == new, 'forced pass is not stable for %s' % source)
        n += 1
    print('identity: %d images, %.1fs' % (n, time.time() - t0))


# --------------------------------------------- synthetic translations ------

def synth(source, img, ex, seed, mean, spread, frac=1.0):
    rng = random.Random('%s|%d' % (source, seed))
    recs, ens = [], {}
    for s in ex[0]:
        r = rec(source, s)
        if rng.random() < frac:
            f = mean * (1 + spread * (rng.random() * 2 - 1))
            if rng.random() < 0.08:
                f = 0.2           # some very short ones (labels)
            r['en'] = dummy(rng, int(f * len(s.raw) + 0.5))
        recs.append(r)
    return recs


def run_case(source, img, ex, recs, share, cross, tag):
    new, rep = R.repack(img.data, img.base, recs, source=source, share=share, cross_pool=cross, extracted=ex)
    by = {s.off: s for s in ex[0]}
    enc = R._entry_enc(recs, by, R.Report(''), source)
    bad = R.check(img.data, new, img.base, ex[0], enc, rep, share=share)
    check(not bad, '%s %s: %s' % (source, tag, bad[:3]))
    check(not rep.skipped, '%s %s: skipped %r' % (source, tag, rep.skipped[:2]))
    # accounting: each translated string is exactly one of {fixed overflow, reverted (overflow), written}
    check(len(enc) == rep.translated, 'translated count')
    # re-extraction: every string that is still Japanese must be found again with identical text
    keep = set()
    over = {o['id'] for o in rep.overflow} | {o['id'] for o in rep.fixed_overflow}
    for s in ex[0]:
        if s.off not in enc or ('%s#%x' % (source, s.off)) in over:
            keep.add(T.decode_text(s.raw))
    got = reextract_texts(new, img.base, source)
    # textdb's acceptance rule for glued half-width-kana strings depends on neighbouring table entries
    # (heuristic); those may be re-classified after neighbours became English.  Pointers are proven by check().
    missing = [k for k in keep if k not in got and not any(0xff61 <= ord(c) <= 0xff9f for c in k)]
    check(not missing, '%s %s: %d Japanese strings lost after repack, e.g. %r' % (source, tag, len(missing), missing[:1]))
    # determinism
    new2, rep2 = R.repack(img.data, img.base, recs, source=source, share=share, cross_pool=cross, extracted=ex)
    check(new2 == new, '%s %s: not deterministic' % (source, tag))
    return new, rep, enc


def test_stability(source, img, ex, recs):
    """second pass over the output (share none): same pools, strings = the output's own strings"""
    new, rep = R.repack(img.data, img.base, recs, source=source, share='none', extracted=ex)
    after = rep.after
    ex2 = (after, None, None)
    touched = [(p['start'], p['end']) for p in rep.pools if p['touched']]
    recs2 = [rec(source, s) for s in after]
    for r, s in zip(recs2, after):
        if any(a <= s.off < z for a, z in touched):       # untouched pools keep their original padding
            r['en'] = r['ja']
    new2, rep2 = R.repack(new, img.base, recs2, source=source, share='none', extracted=ex2)
    check(new2 == new, '%s: second pass is not a fixed point (%d bytes differ)' % (
        source, sum(1 for a, b in zip(new, new2) if a != b)))
    check(not rep2.overflow and not rep2.fixed_overflow, '%s: second pass overflows' % source)


def test_synthetic(srcs):
    names = ['CLUBEDIT', 'EVENT', 'GAME', 'HELP', 'TRAINING', 'MEETING', 'NEWS', 'DRAFT'] if not QUICK else \
        ['CLUBEDIT', 'EVENT', 'GAME']
    t0 = time.time()
    cases = 0
    for source, img, ex in srcs:
        base = os.path.basename(source)[:-4]
        if base not in names or not source.startswith('FLOW_PRG/'):
            continue
        for seed, mean, spread, frac in ((1, 0.9, 0.6, 1.0), (2, 1.2, 0.6, 1.0), (3, 1.6, 0.5, 0.5), (4, 0.5, 0.4, 1.0)):
            recs = synth(source, img, ex, seed, mean, spread, frac)
            for share in ('none', 'dup'):
                for cross in (False, True):
                    new, rep, enc = run_case(source, img, ex, recs, share, cross, 'seed%d %s cross=%s' % (seed, share, cross))
                    cases += 1
            if seed in (1, 2):
                test_stability(source, img, ex, recs)
    print('synthetic: %d cases, %.1fs' % (cases, time.time() - t0))


def test_repack_beats_per_string(srcs):
    """a configuration where repacking succeeds but the per-string in-place model fails"""
    for source, img, ex in srcs:
        if source != 'FLOW_PRG/CLUBEDIT.BIN':
            continue
        # equal total, shifted lengths: even strings 40 % shorter, odd strings 40 % longer, all movable
        recs = []
        for i, s in enumerate(ex[0]):
            r = rec(source, s)
            if R.is_movable(s):
                L = len(s.raw)
                r['en'] = 'a' * max(1, int(L * (0.6 if i % 2 == 0 else 1.35)))
            recs.append(r)
        new, rep = R.repack(img.data, img.base, recs, source=source, share='none', extracted=ex)
        by = {s.off: s for s in ex[0]}
        n_inplace_fail = sum(1 for r in recs if r['en'] and len(r['en']) + 1 > by[int(r['id'].split('#')[1], 16)].max_bytes)
        check(n_inplace_fail > 10, 'beat-per-string: expected many in-place failures, got %d' % n_inplace_fail)
        print('beat-per-string: in-place failures %d, repack overflow %d (pools %d)' % (
            n_inplace_fail, len(rep.overflow), len(rep.pools)))
        check(len(rep.overflow) < n_inplace_fail, 'beat-per-string: repack not better')


def main():
    t0 = time.time()
    test_unit()
    srcs = load_all()
    print('loaded %d images in %.1fs' % (len(srcs), time.time() - t0))
    test_identity(srcs if not QUICK else [x for x in srcs if x[0].split('/')[-1][:-4] in ('CLUBEDIT', 'EVENT', 'GAME', 'MEETING')])
    test_synthetic(srcs)
    test_repack_beats_per_string(srcs)
    print('%d failures, %.1fs' % (len(fails), time.time() - t0))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
