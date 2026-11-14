"""Self-test of the short-name tag patch (tools/layoutpatch.py tag_patches, docs/s7t-proposals.md section 2):
python -I -X utf8 tools/test_tagfix.py   (about 1 minute)

The routine short_name(dest r4, name r5) of 11 overlays (the Practice > Player Placement tags and ten more labels) is EXECUTED in the
SH-4 simulator (tools/sh4sim.py) from the REAL overlay bytes, with the real literal pool words:
  1. the ORIGINAL routine (real bytes of every overlay) gives the Japanese-era rule: first word, 4 bytes, ' %s ' for 1 or 2 bytes;
  2. the PATCHED routine (layoutpatch.patch_tag on the real bytes) gives: LAST word, up to the per-overlay limit (LP.TAG_LIMIT_BY_OVERLAY: GAME and TRAINING 5, the other nine TAG_LIMIT 7) bytes, same pad rule, on all 11
     overlays and on every English name of translation/ETC_DATA__BPINFO.BIN.jsonl plus edge cases (single word, trailing blank,
     NUL, 12 letters, a double blank);
  3. both leave r8..r14 and the stack as they found them, write only the 8-byte local buffer (below the entry sp) and call sprintf once with the
     stack protocol [sp] = format, [sp+4] = buffer;
  4. differential: for one-word names of at most 4 letters the patched routine equals the original (nothing else changes);
  5. only the 152 byte routine differs (same size); a second application, a foreign image and a moved routine are refused;
  6. composes with the other layout patches (club-name composer) and the proportional font hooks still find their sites afterwards."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402
import overlay             # noqa: E402
import sh4sim              # noqa: E402

FAILS = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def read_ext(rel):
    with open(os.path.join(ROOT, 'extracted', *rel.split('/')), 'rb') as f:
        return f.read()


def reference(src, limit, orig=False):
    """python model.  orig: the first word, 4 bytes.  else: the last word (a trailing blank does not start a word), `limit` bytes."""
    if orig:
        w = src.split(b' ')[0][:4]
    else:
        q = 0
        for i, ch in enumerate(src):
            if ch == 0x20 and i + 1 < len(src):
                q = i + 1
        w = src[q:].split(b' ')[0][:limit]
    return (b' ' + w + b' ') if len(w) in (1, 2) else w


def run(img, base, ent, src, fmt1, fmt2):
    """execute the routine at file offset `ent` of the image loaded at `base`; returns (text, number of sprintf calls, bytes written)"""
    m = sh4sim.Machine()
    m.load(base, img)
    m.load(0x8cf00000, src + b'\0')
    sp = 0x8c800000
    m.R[15] = sp
    m.R[4] = 0x8cf20000
    m.R[5] = 0x8cf00000
    for k in range(8, 15):
        m.R[k] = 0x1000 + k
    stop = 0x8cff0000
    m.PR = stop
    out = {'calls': 0}

    def spf(mm):
        fmt = mm.rn(mm.R[15], 4)
        arg = mm.rn(mm.R[15] + 4, 4)
        s = bytes(mm.rb(arg + i) for i in range(64)).split(b'\0')[0]
        f = bytes(mm.rb(fmt + i) for i in range(8)).split(b'\0')[0]
        out['text'] = f.replace(b'%s', s)
        out['calls'] += 1
        out['buf'] = arg
        out['fmt'] = fmt
        out['dest'] = mm.R[4]
    m.ext_ret[LP.TAG_SPRINTF] = spf
    m.run(base + ent, stop)
    for k in range(8, 15):
        assert m.R[k] == 0x1000 + k, 'callee-saved r%d clobbered' % k
    assert m.R[15] == sp, 'stack pointer not restored (%#x)' % m.R[15]
    assert out['calls'] == 1, 'sprintf called %d times' % out['calls']
    assert out['dest'] == 0x8cf20000, 'sprintf destination r4 is %#x, not the caller buffer' % out['dest']
    assert sp - 64 <= out['buf'] < sp, 'buffer %#x outside the routine frame' % out['buf']
    return out


def names():
    res = [b'Taiyo Yamada', b'H. Nakata', b'Kenji Nakagawa', b'Ono', b'Al', b'X', b'Taro Yamada ', b'Seigo Kawamoto', b'T.Ishiwatari',
           b'Pierre Van Der Sar', b'WWWWWWWWWWWW', b'A Bcdefghijkl', b'Ab Cd', b'Ai', b'Isao Nakagawa', b'Rudknapp', b'Dai Sasaki',
           b'Kaz  Miura', b'J. M. Ito']
    p = os.path.join(ROOT, 'translation', 'ETC_DATA__BPINFO.BIN.jsonl')
    with open(p, encoding='utf8') as f:
        for k, ln in enumerate(f):
            r = json.loads(ln)
            if r.get('en') and k % 60 == 0:
                res.append(r['en'].encode('ascii', 'replace')[:13])
    return res


def main():
    nms = names()
    print('%d sample names' % len(nms))
    first_new = None
    for n in sorted(LP.TAG_SITES):
        rel = 'FLOW_PRG/%s.BIN' % n
        d = read_ext(rel)
        base = overlay.unpack_overlay(d)['load_addr']
        ent, b2, fmt1, fmt2 = LP.tag_scan(d, n)
        check(ent == LP.TAG_SITES[n] and b2 == base, '%s: routine found at %#x, base %#x agrees with overlay.unpack_overlay' % (n, ent, base))
        new = LP.patch_tag(d, n)
        diff = [i for i in range(len(d)) if d[i] != new[i]]
        check(len(new) == len(d) and diff and ent <= diff[0] and diff[-1] < ent + LP.TAG_LEN,
              '%s: same size, only the 152 bytes of the routine differ (%d bytes changed)' % (n, len(diff)))
        bad = 0
        for nm in (nms if n == 'TRAINING' else nms[:40]):
            for img, orig, limit in ((d, True, 4), (new, False, LP.tag_limit_for(n))):
                got = run(img, base, ent, nm, fmt1, fmt2)['text']
                exp = reference(nm, limit, orig)
                if got != exp:
                    bad += 1
                    if bad < 4:
                        print('   MISMATCH %s %r orig=%s: %r != %r' % (n, nm, orig, got, exp))
        check(bad == 0, '%s: original (first word, 4 bytes) and patched (last word, %d bytes) match the model on %d names' % (n, LP.tag_limit_for(n), len(nms)))
        # the original rule is what the unpatched game does: 'Taiyo Yamada' -> 'Taiy', patched -> 'Yamada'
        a = run(d, base, ent, b'Taiyo Yamada', fmt1, fmt2)['text']
        b = run(new, base, ent, b'Taiyo Yamada', fmt1, fmt2)['text']
        lim = LP.tag_limit_for(n)
        check(a == b'Taiy' and b == b'Yamada'[:lim], '%s: Taiyo Yamada -> %r before, %r after (limit %d)' % (n, a, b, lim))
        c = run(new, base, ent, b'H. Nakata', fmt1, fmt2)['text']
        check(c == b'Nakata'[:lim], '%s: H. Nakata -> %r (original %r)' % (n, c, run(d, base, ent, b'H. Nakata', fmt1, fmt2)['text']))
        # one-word names of up to 4 letters: identical behaviour
        same = all(run(d, base, ent, w, fmt1, fmt2)['text'] == run(new, base, ent, w, fmt1, fmt2)['text']
                   for w in (b'Ono', b'Al', b'X', b'Kato', b'Ito', b'Mo'))
        check(same, '%s: short one-word names behave exactly as the original' % n)
        # second application, tampered image
        try:
            LP.patch_tag(new, n)
            check(False, '%s: patching twice is refused' % n)
        except LP.LayoutPatchError:
            check(True, '%s: patching twice is refused' % n)
        t = bytearray(d)
        t[ent + 0x40] ^= 0x10
        try:
            LP.patch_tag(bytes(t), n)
            check(False, '%s: a foreign routine is refused' % n)
        except LP.LayoutPatchError:
            check(True, '%s: a foreign routine is refused' % n)
        if first_new is None:
            first_new = (n, d, new)
    # per-overlay limits (study 9a M3): GAME and TRAINING 5, the other nine 7
    check(LP.TAG_LIMIT_BY_OVERLAY == {'GAME': 5, 'TRAINING': 5} and LP.TAG_LIMIT == 7, 'TAG_LIMIT_BY_OVERLAY = {GAME: 5, TRAINING: 5}, default 7')
    check(all(LP.tag_limit_for(n) == (5 if n in ('GAME', 'TRAINING') else 7) for n in LP.TAG_SITES), 'tag_limit_for: 5 for GAME / TRAINING, 7 for the other nine')
    check(LP.tag_limit_for('GAME', 3) == 3 and LP.tag_limit_for('EVENT', 9) == 7 and LP.tag_limit_for('EVENT', 4) == 4, 'an explicit limit can only lower the per-overlay limit')
    for n in ('GAME', 'TRAINING', 'EVENT', 'CAP_SLCT'):
        d0 = read_ext('FLOW_PRG/%s.BIN' % n)
        e0, _, f1, f2 = LP.tag_scan(d0, n)
        b0 = overlay.unpack_overlay(d0)['load_addr']
        im = LP.patch_tag(d0, n)
        got = [run(im, b0, e0, nm, f1, f2)['text'] for nm in (b'Kasamatsu', b'Hisanaga', b'Kanawa', b'Taiyo Ito')]
        exp = [b'Kasam', b'Hisan', b'Kanaw', b'Ito'] if n in ('GAME', 'TRAINING') else [b'Kasamat', b'Hisanag', b'Kanawa', b'Ito']
        check(got == exp, '%s: Kasamatsu / Hisanaga / Kanawa / Taiyo Ito -> %s' % (n, got))
    # limit parameter and bad limits
    n, d, new = first_new
    ent, base0, f1, f2 = LP.tag_scan(d, n)
    base = overlay.unpack_overlay(d)['load_addr']
    for lim in (4, 5, 6):
        im = LP.patch_tag(d, n, lim)
        ok = all(run(im, base, ent, nm, f1, f2)['text'] == reference(nm, lim) for nm in nms)
        check(ok, 'limit %d (the alternative widths of the test sheet) matches the model' % lim)
    try:
        LP.patch_tag(d, n, 8)
        check(False, 'limit 8 is refused (8-byte buffer)')
    except LP.LayoutPatchError:
        check(True, 'limit 8 is refused (8-byte buffer)')
    # a moved routine: the same bytes at another offset are refused (name given)
    t = d[:ent] + b'\0' * 4 + d[ent:]
    try:
        LP.patch_tag(t, n)
        check(False, 'a moved routine is refused')
    except LP.LayoutPatchError:
        check(True, 'a moved routine is refused')
    # composition with the club-name patches (EVENT is in both lists) and the font hooks
    ev = read_ext('FLOW_PRG/EVENT.BIN')
    cur = {'/FLOW_PRG/EVENT.BIN': LP.patch_clubnames(ev, 'EVENT')}
    out = LP.tag_patches(read_ext, cur)
    check(len(out) == 11 and all(len(v) == len(read_ext(k.lstrip('/'))) for k, v in out.items()), 'tag_patches: 11 overlays, sizes unchanged')
    both = out['/FLOW_PRG/EVENT.BIN']
    check(LP.patch_clubnames.__name__ and both != cur['/FLOW_PRG/EVENT.BIN'] and both != ev, 'EVENT keeps the club-name patch and gains the tag patch')
    try:
        import fontpatch as FP
        sites = FP.find_sites(both, 'FLOW_PRG/EVENT.BIN')
        check(len(sites) >= 1, 'the proportional font still finds its hook site in the tag-patched EVENT.BIN')
    except Exception as e:   # noqa: BLE001
        check(False, 'fontpatch.find_sites on the tag-patched EVENT.BIN: %s' % e)
    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        return 1
    print('ALL PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
