"""Self-test of tools/layoutpatch.py: python -I -X utf8 tools/test_layoutpatch.py  (about 1 minute).

1. HOMETOWN list-label spacer: the routine at 0x8c2d2a50 is EXECUTED in the SH-4 simulator (tools/sh4sim.py) before and after the patch.
2. club / hometown name composition: the 20 overlays are patched (5 bytes each, 10 in HOMETOWN with the spacer; the bounded composer
   replaces the 232 byte body in addition, and in HOMETOWN the sprintf literal of the candidate popup is retargeted), refused a second
   time, and the composer (0x8c2e072a, town_short / pref_short / sprintf) is EXECUTED in the simulator: original -> KagoshiMythos,
   patched without the guard -> Kagoshima Mythos, with the guard -> Kagos. Mythos (13 characters at most).
3. club-name guard (docs/layout-issues.md section 9): the bounded composer (BPMATCH copy; HOMETOWN's own copy is dead code and becomes
   the join of the candidate popup) is executed on the Japanese pool of the extracted overlay (every 5th municipality x 55 words x 2
   modes, the prefecture pairs x 2 modes), against the Python reference rule, with write watching (nothing outside the 14 byte buffer),
   canary bytes, NUL, length <= 13, and out-of-range arguments; the same on three other overlay copies and on the popup join;
   guard=False, dot=False, room.  The exhaustive run on the real built overlays is tools/re/ovf_sim.py --all."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 're'))
sys.path.insert(0, os.path.join(HERE, 're', 'layout'))
sys.path.insert(0, os.path.join(HERE, 're', 'hnm'))
import layoutpatch as LP  # noqa: E402
import sim_hometown_label as SIM  # noqa: E402
import hnm_sim_club as CLUB  # noqa: E402
import ovf_sim as OVF  # noqa: E402

FAILS = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def main():
    first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    orig = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
    new = LP.patch_hometown(orig)
    diff = [i for i in range(len(orig)) if orig[i] != new[i]]
    check(len(new) == len(orig) and diff == [0x2ab4, 0x2ade], 'only the two cmp/eq immediates change (%s)' % [hex(i) for i in diff])
    try:
        LP.patch_hometown(new)
        check(False, 'patching twice is refused')
    except LP.LayoutPatchError:
        check(True, 'patching twice is refused')
    try:
        LP.patch_hometown(orig[:0x2ab4] + b'\0\0' + orig[0x2ab6:])
        check(False, 'unexpected bytes are refused')
    except LP.LayoutPatchError:
        check(True, 'unexpected bytes are refused')
    expect_orig = {'Tohoku': b' To ho ku', 'Kansai': b' Ka ns ai', 'Kyushu': b' Ky us hu', 'Kanto': b' Kanto', 'Hokkaido': b' Hokkaido',
                   'Okinawa': b' Okinawa', 'Nara': b' Na\x81\x40ra', 'Aioi': b' Ai\x81\x40oi', 'Izu': b' Izu', 'Mie': b' Mie'}
    for w, e in expect_orig.items():
        a = SIM.label(orig, first, w.encode('ascii'))
        b = SIM.label(new, first, w.encode('ascii'))
        check(a == e, 'original %-9s -> %r' % (w, a))
        check(b == b' ' + w.encode('ascii'), 'patched  %-9s -> %r' % (w, b))
    # Japanese words keep working (plain, no justification)
    for w in ('東北', '北海道'):
        b = SIM.label(new, first, w.encode('cp932'))
        check(b == b' ' + w.encode('cp932'), 'patched Japanese %s -> %r' % (w, b.decode('cp932')))
    # composes on the current bytes (the spacer patch plus the club-name patch)
    rd = lambda p: open(os.path.join(ROOT, 'extracted', p), 'rb').read()      # noqa: E731
    out = LP.make_patches(rd, {LP.HOMETOWN_ISO: orig})
    check(out[LP.HOMETOWN_ISO] == LP.patch_clubnames(new, 'HOMETOWN'), 'make_patches composes on the current bytes')
    check(sorted(out) == sorted('/FLOW_PRG/%s.BIN' % n for n in LP.CLUB_OVERLAYS) and len(out) == 20, 'make_patches covers the 20 composer overlays')
    out_ng = LP.make_patches(rd, {LP.HOMETOWN_ISO: orig}, guard=False)
    for iso, nb in sorted(out.items()):
        ob = rd(iso.lstrip('/'))
        a = ob.find(LP.CLUB_SIG_A)
        c = a + LP.COMP_DELTA
        diff = [i for i in range(len(ob)) if ob[i] != nb[i]]
        outside = [i for i in diff if not c <= i < c + LP.COMP_LEN]
        ng = out_ng[iso]
        nd = [i for i in range(len(ob)) if ob[i] != ng[i]]
        extra = sorted(set(outside) - set(nd))                    # HOMETOWN: the retargeted sprintf literal of the candidate popup
        ok_extra = (len(extra) == 0) if iso != LP.HOMETOWN_ISO else (0 < len(extra) <= 4 and extra[-1] - extra[0] < 4)
        check(len(nb) == len(ob) and not (set(nd) - set(outside)) and ok_extra,
              '%-26s same size, %d bytes differ outside the composer (+%d: popup literal), composer replaced' % (iso, len(outside), len(extra)))
        check(len(nd) == (10 if iso == LP.HOMETOWN_ISO else 5) and ng[c:c + LP.COMP_LEN] == ob[c:c + LP.COMP_LEN],
              '%-26s guard=False: only the %d bytes of the join patch differ, composer kept' % (iso, len(nd)))
        try:
            LP.patch_clubnames(nb, iso)
            check(False, '%s: second application refused' % iso)
        except LP.LayoutPatchError:
            pass
    check(True, 'second application refused in all 20')
    # the composer, executed (the original and the unguarded join, HOMETOWN's own copy)
    eng = CLUB.with_english(orig)
    pat = LP.patch_clubnames(eng, 'HOMETOWN', guard=False)
    exp = {(1223, 0, 46, 0): (b'KagoshiMythos', b'Kagoshima Mythos'), (1223, 0, 46, 1): (b'MythosKagoshi', b'Mythos Kagoshima'),
           (1223, 46, 46, 2): (b'KagoshiMythos', b'Kagoshima Mythos'), (1223, 13, 11, 3): (b'ShadowsKanaga', b'Shadows Kanagawa'),
           (1223, 14, 11, 2): (b'IzuShadows', b'Izu Shadows')}
    for args, (e_old, e_new) in exp.items():
        a = CLUB.compose(eng, first, *args)
        b = CLUB.compose(pat, first, *args)
        check(a == e_old and b == e_new, 'composer %s: original %r -> patched (guard=False) %r' % (args, a.decode(), b.decode()))
    # Japanese is untouched in meaning except that the 2-byte suffix is no longer cut: it keeps the Japanese 市 / 県
    ja_old = CLUB.compose(orig, first, 456, 13, 11, 0)
    ja_new = CLUB.compose(LP.patch_clubnames(orig, 'HOMETOWN', guard=False), first, 456, 13, 11, 0)
    check(ja_old.decode('cp932') == '横浜' + 'ｼｬﾄﾞｳｽﾞ' and ja_new.decode('cp932') == '横浜市 ｼｬﾄﾞｳｽﾞ',
          'Japanese data: original %r (strip 市), patched %r' % (ja_old.decode('cp932'), ja_new.decode('cp932')))

    # ---- the guard -------------------------------------------------------------------------------------------------------------
    bp_orig = rd('FLOW_PRG/BPMATCH.BIN')
    bp = LP.patch_clubnames(bp_orig, 'BPMATCH')
    bp_eng = OVF.synth_english(bp)
    cg = OVF.Composer(bp_eng, first)
    exp_g = {(1223, 0, 46, 0): b'Kagos. Mythos', (1223, 0, 46, 1): b'Mythos Kagos.', (1223, 46, 46, 2): b'Kagos. Mythos',
             (1223, 13, 11, 3): b'Shadows Kana.', (1223, 14, 11, 2): b'Izu Shadows', (1223, 0, 11, 0): b'Kago. Shadows'}
    for args, e in exp_g.items():
        r = cg.compose(*args)
        check(r[0] == e and not r[2] and not r[3] and r[1] == len(e) and r[5], 'composer (BPMATCH) %s -> %r' % (args, r[0].decode()))
    code = LP.composer_bytes(0x8c2e072a)
    check(len(code) <= LP.COMP_LEN and LP.composer_bytes(0x8c2e072a, dot=False) != code,
          'bounded composer is %d bytes (budget %d)' % (len(code), LP.COMP_LEN))
    pcode = LP.composer_bytes(0x8c2e072a, popup_word=0x8c336a14)
    check(len(pcode) <= LP.COMP_LEN, 'popup join entry is %d bytes (budget %d)' % (len(pcode), LP.COMP_LEN))
    try:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)
        bad = [i for i in range(0, len(code), 2) if not list(md.disasm(code[i:i + 2], 0x8c2e072a + i))]
        bad += [i for i in range(0, len(pcode) - 8, 2) if not list(md.disasm(pcode[i:i + 2], 0x8c2e072a + i))]
        check(not bad, 'every code word of both entries decodes in capstone %s' % bad[:3])
    except ImportError:
        print('skip capstone cross-check (not installed)')
    ja = OVF.Composer(bp, first).compose(456, 13, 11, 0)
    check(len(ja[0]) <= 13 and not ja[2], 'Japanese data with the guard: %d bytes (a double byte character may be cut when kanji + 7 half-width kana do not fit)' % len(ja[0]))
    comp = OVF.Composer(bp, first)
    towns, prefs, pool = comp.tables()
    problems = []
    cut = 0
    runs = 0
    for t in range(1, len(towns) + 1, 5):
        for w in range(len(pool)):
            for mode in (0, 1):
                _o, tr = OVF.check_one(comp, 'town', t, w, mode, towns, prefs, pool, True, problems)
                cut += tr
                runs += 1
    for p in range(0, 49):
        for w in range(0, len(pool), 3):
            for mode in (2, 3):
                OVF.check_one(comp, 'pref', p, w, mode, towns, prefs, pool, True, problems)
                runs += 1
    check(not problems, 'bounded composer (Japanese pool): %d runs (%d needing a cut): no write beyond 14 bytes, NUL, <= 13, equals the reference %s' % (runs, cut, problems[:2]))
    pr = OVF.robustness(comp)
    check(not pr, 'bounded composer: out-of-range municipality / prefecture / word / mode stay inside the buffer %s' % (pr[:1],))
    # a word of 8 characters: the town keeps 4; a (hypothetical) 12 character word is cut (never real here: the longest is 8)
    for word, cond in ((b'Abcdefgh', lambda o: len(o) == 13 and o.endswith(b' Abcdefgh')), (b'Abcdefghijkl', lambda o: len(o) <= 13)):
        im = OVF.synth_english(bp, towns={1: b'Kagoshima'}, pool={7: word})
        r = OVF.Composer(im, first).compose(1, 0, 7, 0)
        check(cond(r[0]) and not r[2] and not r[3], 'club word %r: %r' % (word.decode(), r[0]))
    # dot=False: the cut town has no dot; room: a larger buffer (only if ever proven) keeps the longer name; absurd values are refused
    cnd = OVF.Composer(OVF.synth_english(LP.patch_clubnames(bp_orig, 'BPMATCH', dot=False)), first)
    check(cnd.compose(1223, 0, 46, 0)[0] == b'Kagosh Mythos', 'dot=False: Kagosh Mythos')
    crm = OVF.Composer(OVF.synth_english(LP.patch_clubnames(bp_orig, 'BPMATCH', room=19)), first)
    check(crm.compose(1223, 0, 46, 0)[0] == b'Kagoshima Mythos', 'room=19: Kagoshima Mythos is kept')
    try:
        LP.patch_clubnames(bp_orig, 'BPMATCH', room=300)
        check(False, 'room=300 is refused')
    except LP.LayoutPatchError:
        check(True, 'room=300 is refused')
    # other copies of the library (other load bases; CSAVE3 is linked against another 1ST_READ build): same code, other literals
    for n in ('EVENT', 'ENDOPT', 'CSAVE3'):
        im = LP.patch_clubnames(rd('FLOW_PRG/%s.BIN' % n), n)
        cx = OVF.Composer(im, first)
        tw, pf, pl = cx.tables()
        pb = []
        for t in range(1, len(tw) + 1, 37):
            for w in range(0, len(pl), 4):
                for mode in (0, 1):
                    OVF.check_one(cx, 'town', t, w, mode, tw, pf, pl, True, pb)
        check(not pb, '%s (base %#x): bounded composer sample ok %s' % (n, cx.base, pb[:1]))

    # ---- HOMETOWN: the candidate popup join (HOMETOWN's composer copy is dead code and is replaced by it) -----------------------
    ht = LP.patch_clubnames(new, 'HOMETOWN')
    pj = OVF.Popup(OVF.synth_english(ht), first)
    check(pj.lit_sprintf == pj.comp, 'HOMETOWN: the popup sprintf literal points at the join entry (%#x)' % pj.comp)
    for a_, b_, w_, e in ((b'Kagoshima', b'Mythos', 'b', b'Kagos. Mythos'), (b'Mythos', b'Kagoshima', 'a', b'Mythos Kagos.'),
                          (b'Aomori', b'Dummy', 'b', b'Aomori Dummy'), (b'Ginowan', b'Topolino', 'b', b'Gin. Topolino')):
        r = pj.join(a_, b_, w_)
        check(r[0] == e and not r[2] and not r[3] and r[5] and r[1] == len(e),
              'popup join %r + %r -> %r (caller strings untouched, stack balanced)' % (a_.decode(), b_.decode(), r[0].decode()))
    ptowns, pprefs, ppool = pj.tables()
    jp = []
    jruns = 0
    for t in range(1, len(ptowns) + 1, 7):
        for w in range(0, len(ppool), 2):
            for first_ in ('a', 'b'):
                tw_, wd_ = ptowns[t - 1], ppool[w]
                r = pj.join(tw_, wd_, 'b') if first_ == 'a' else pj.join(wd_, tw_, 'a')
                jruns += 1
                want = OVF.reference(tw_, wd_, first_ == 'b', True)
                if r[0] != want or r[2] or r[3] or not r[5] or len(r[0]) > 13:
                    jp.append((t, w, first_, r[0], want))
    check(not jp, 'popup join: %d runs on the Japanese pool, both orders, equals the reference, nothing beyond 14 bytes %s' % (jruns, jp[:2]))
    live = bytearray(new)
    at = len(live) // 4 * 4 - 4
    live[at:at + 4] = (0x8c2d0000 + 0x1072a).to_bytes(4, 'little')
    try:
        LP.patch_clubnames(bytes(live), 'HOMETOWN')
        check(False, 'a composer copy that is referenced is not replaced by the popup join')
    except LP.LayoutPatchError:
        check(True, 'a composer copy that is referenced is not replaced by the popup join')
    print('FAILED %d' % len(FAILS) if FAILS else 'ALL PASSED')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
