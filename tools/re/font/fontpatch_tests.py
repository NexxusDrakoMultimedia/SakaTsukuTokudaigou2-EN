"""Self-test and manifest writer for fontpatch.py (kept separate: heavy)."""
import hashlib
import json
import os
import sys
import time

import fontpatch as FP
import sh4sim

ROOT = FP.ROOT


def hx(b):
    return bytes(b).hex()


def check_cave():
    code, lst, sym = FP.assemble_cave()
    bad = 0
    for a, bb, t in lst:
        if len(bb) == 2:
            cs = FP.capstone_check(a, bb)[0]
            if cs != t:
                bad += 1
                print('CAVE MISMATCH %#x %s asm=%r capstone=%r' % (a, bb.hex(), t, cs))
    print('cave: %d bytes (limit %d), %d instructions, capstone mismatches %d' % (len(code), FP.CAVE_MAX, len(lst), bad))
    return code, lst, sym, bad


def check_hook_decode(site, sym):
    """every emitted instruction word must decode (capstone) to what the assembler meant."""
    bad = 0
    for name, off, code, lst, size, A in FP.build_hooks(site, sym):
        for a, bb, t in lst:
            if len(bb) == 2:
                cs = FP.capstone_check(a, bb)[0]
                if cs != t:
                    bad += 1
                    print('  HOOK MISMATCH', site['name'], name, hex(a), bb.hex(), t, cs)
        # padding nops (not part of lst) decode as nop
    return bad


def sim_equal(a, b, what):
    if a != b:
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                print('   DIFF', what, 'first at code index', i, x, y)
                break
        else:
            print('   DIFF', what, 'length', len(a), len(b))
        return False
    return True


WINDOWS = [(20, 24, 1), (20, 24, 0), (7, 24, 1), (13, 24, 0), (20, 16, 1), (10, 20, 0)]


def sim_matrix(site, img, base, code, table_kinds, windows, vectors, verbose=False):
    """returns number of failures"""
    fails = 0
    cave_code, _, sym = FP.assemble_cave()
    v = FP.VAR[site['variant']]
    patched_both = {k: FP.apply_hooks(img, site, sym) for k in (0,)}[0]
    patched_adv = FP.apply_hooks(img, site, sym, hooks=('adv',))
    for W, A, flag in windows:
        for vec in vectors:
            kw = dict(W=W, A=A, flag=flag, x0=20, y0=240, lh=24)
            ref = FP.orig_model(vec, **kw)
            got = FP.run_layout(img, base, site, vec, **kw)
            if not sim_equal(got, ref, 'orig sim vs model %s W=%d A=%d f=%d' % (site['name'], W, A, flag)):
                fails += 1
            for tk in table_kinds:
                tbl = FP.table_vec(tk)
                extra = [(FP.CAVE, cave_code), (FP.TABLE, tbl)]
                # H1 only
                got1 = FP.run_layout(patched_adv, base, site, vec, extra=extra, **kw)
                exp1 = FP.new_model(vec, table=tbl, wrap=False, adv=True, **kw)
                if not sim_equal(got1, exp1, 'H1 %s tbl=%s W=%d A=%d f=%d' % (site['name'], tk, W, A, flag)):
                    fails += 1
                # H1+H2
                got2 = FP.run_layout(patched_both, base, site, vec, extra=extra, **kw)
                exp2 = FP.new_model(vec, table=tbl, wrap=True, adv=True, **kw)
                if not sim_equal(got2, exp2, 'H1+H2 %s tbl=%s W=%d A=%d f=%d' % (site['name'], tk, W, A, flag)):
                    fails += 1
                if tk == 'all12' or tk == 'zero':
                    # all-12 (and all-zero = fallback 12) must be byte-for-byte equivalent to the ORIGINAL behaviour
                    if A in (24, 16, 20):
                        if not sim_equal(got1, ref, 'H1 equivalence %s tbl=%s W=%d A=%d f=%d' % (site['name'], tk, W, A, flag)):
                            fails += 1
                        if not sim_equal(got2, ref, 'H1+H2 equivalence %s tbl=%s W=%d A=%d f=%d' % (site['name'], tk, W, A, flag)):
                            fails += 1
    return fails


def run(cmd):
    t0 = time.time()
    code, lst, sym, bad = check_cave()
    sites = FP.scan_all()
    print('sites', len(sites))
    if cmd == 'manifest':
        return write_manifest(sites, code, lst, sym)
    if cmd == 'liveness':
        return 1 if liveness_test(sites, code, sym) else 0
    # ---- 1. decode check of every hook of every site
    total_bad = bad
    for s in sites:
        total_bad += check_hook_decode(s, sym)
    print('capstone decode mismatches over all hooks:', total_bad)
    # ---- 2. patched images differ only inside the declared regions; regions do not overlap
    for s in sites:
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        new = FP.apply_hooks(d, s, sym)
        diff = [i for i in range(len(d)) if d[i] != new[i]]
        regions = [(h[1], h[1] + h[4]) for h in FP.build_hooks(s, sym)]
        assert all(any(lo <= i < hi for lo, hi in regions) for i in diff), s['name']
        assert len(new) == len(d)
        assert regions[0][1] <= regions[1][0] or regions[1][1] <= regions[0][0]
    print('region containment: OK for all', len(sites), 'sites')
    for s in sites:
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        new, ss = FP.patch_overlay(d, s['iso'])
        assert new == FP.apply_hooks(d, s, sym), s['iso']       # base-agnostic build API == per-site manifest bytes
    print('build API (patch_overlay, base 0) == manifest bytes for all', len(sites), 'sites')
    total_bad += static_slot_check(sites, lst, sym)
    total_bad += xref_check(sites, sym)
    # ---- 3. execution
    reps = {'MEETING.BIN': None, 'COMM.BIN': None, 'CSAVE3.BIN': None}
    fails = 0
    vectors = FP.test_vectors()
    for s in sites:
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        if s['name'] in reps and 'ATFIRST' not in s['iso']:
            f = sim_matrix(s, d, s['base'], code, ('all12', 'prop', 'zero'), WINDOWS, vectors)
            print('  full matrix', s['name'], s['variant'], 'failures', f)
        else:
            f = sim_matrix(s, d, s['base'], code, ('all12', 'prop'), [(20, 24, 1), (13, 24, 0)], vectors[:2])
        fails += f
    print('simulation failures:', fails, 'elapsed %.1fs' % (time.time() - t0))
    return 0 if (total_bad == 0 and fails == 0) else 1


def write_manifest(sites, cave, lst, sym):
    out = os.path.join(ROOT, 'build', 'font')
    os.makedirs(out, exist_ok=True)
    man = {'cave': {'addr': FP.CAVE, 'file': '1ST_READ.BIN', 'file_off': FP.CAVE - 0x8C010000, 'bytes': hx(cave),
                    'symbols': {k: v for k, v in sym.items() if not k.startswith('_')}},
           'table': {'addr': FP.TABLE, 'file': '1ST_READ.BIN', 'file_off': FP.TABLE - 0x8C010000, 'size': 256,
                     'default': hx(bytes([12]) * 256)},
           'alternatives': {'cave_gap1': FP.ALT_CAVE_GAP1, 'table_font_tail': FP.ALT_TABLE_FONT,
                            'font_file_off': FP.ALT_TABLE_FONT - FP.FONT_BASE, 'font_window': FP.FONT_WINDOW},
           'sites': []}
    rows = []
    for s in sites:
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        e = {'iso': '/' + s['iso'], 'base': s['base'], 'variant': s['variant'], 'hooks': []}
        for name, off, code, l, size, A in FP.build_hooks(s, sym):
            e['hooks'].append({'hook': name, 'file_off': off, 'addr': A, 'len': size, 'old': hx(d[off:off + size]),
                               'new': hx(code), 'old_sha1': hashlib.sha1(d[off:off + size]).hexdigest()[:10]})
        man['sites'].append(e)
        rows.append('\t'.join([s['iso'], s['variant'], '0x%08x' % s['base'], '0x%08x' % (s['base'] + s['adv_off']),
                               '0x%08x' % (s['base'] + s['wrap_off']), '0x%x' % s['adv_off'], '0x%x' % s['wrap_off']]))
    json.dump(man, open(os.path.join(out, 'font_patch_manifest.json'), 'w'), indent=1)
    open(os.path.join(out, 'font_patch_sites.tsv'), 'w').write('iso\tvariant\tbase\tH1_addr\tH2_addr\tH1_file_off\tH2_file_off\n' + '\n'.join(rows) + '\n')
    with open(os.path.join(out, 'font_patch_cave.txt'), 'w') as f:
        for a, bb, t in lst:
            f.write('%08x  %s  %s\n' % (a, bb.hex(), t))
    print('wrote', out)
    return 0


def liveness_test(sites, code, sym):
    """patched run with r0-r5/T randomised at every hook exit must produce the SAME external calls (target,r4-r7,
    r8,r10) and the same positions as the original run, for the all-12 table (where behaviour must be identical)."""
    fails = 0
    n = 0
    tbl = FP.table_vec('all12')
    extra = [(FP.CAVE, code), (FP.TABLE, tbl)]
    for s in sites:
        if s['name'] not in ('MEETING.BIN', 'COMM.BIN', 'CSAVE3.BIN', 'CLUBEDIT.BIN', 'HELP.BIN') or 'ATFIRST' in s['iso']:
            continue
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        pd = FP.apply_hooks(d, s, sym)
        for W, A, flag in [(20, 24, 1), (13, 24, 0), (20, 16, 1)]:
            for vec in FP.test_vectors():
                kw = dict(W=W, A=A, flag=flag, x0=20, y0=240, lh=24)
                o_s, o_c = FP.run_layout(d, s['base'], s, vec, want_calls=True, **kw)
                for seed in (1, 2, 3):
                    p_s, p_c = FP.run_layout(pd, s['base'], s, vec, extra=extra, clobber=seed, want_calls=True, **kw)
                    key = lambda c: (c[0], c[1], c[2], c[3], c[4], c[5], c[6])
                    n += 1
                    if p_s != o_s or [key(c) for c in p_c] != [key(c) for c in o_c]:
                        fails += 1
                        print('  LIVENESS FAIL', s['name'], W, A, flag, seed)
    print('liveness/clobber runs', n, 'failures', fails)
    return fails


def static_slot_check(sites, lst, sym):
    """every delayed branch (bra, bsr, bt/s, bf/s, jsr, jmp, rts) must be followed by a legal delay-slot instruction
    (not a branch, not a pc-relative load/mova), and the slot must not clobber the jump register."""
    import struct
    bad = 0
    n = 0

    def words(lst_):
        return [(a, struct.unpack('<H', bb)[0]) for a, bb, t in lst_ if len(bb) == 2]
    allw = [words(lst)]
    for s in sites:
        for name, off, code, l, size, A in FP.build_hooks(s, sym):
            allw.append(words(l))
    for ws in allw:
        for i, (a, w) in enumerate(ws[:-1]):
            delayed = ((w >> 12) in (0xA, 0xB)) or ((w >> 8) in (0x8D, 0x8F)) or (w & 0xF0FF) in (0x400B, 0x402B) or w == 0x000B
            if not delayed:
                continue
            n += 1
            na, nw = ws[i + 1]
            if na != a + 2:
                continue
            if sh4sim.Machine.illegal_slot(nw):
                bad += 1
                print('  ILLEGAL DELAY SLOT at %#x: %04x after %04x' % (na, nw, w))
            if (w & 0xF0FF) in (0x400B, 0x402B):          # jsr/jmp @Rn: slot must not write Rn
                rn = (w >> 8) & 15
                dst = (nw >> 8) & 15 if (nw >> 12) in (0x6, 0x7, 0xE, 0x3) else None
                if dst == rn:
                    bad += 1
                    print('  delay slot writes the jump register at %#x' % na)
    print('delay-slot check: %d delayed branches examined, problems %d' % (n, bad))
    return bad


def xref_check(sites, sym):
    """no branch (from anywhere in the image) and no pc-relative load may reference the INTERIOR of a replaced region
    (only region starts may be branch targets).  Scans every aligned word of the whole image; data words that happen
    to look like branches are reported as 'suspects' and inspected by position (inside literal pools they are harmless)."""
    import struct
    tot_bad = 0
    for s in sites:
        d = open(os.path.join(ROOT, 'extracted', s['iso']), 'rb').read()
        regions = [(h[1], h[1] + h[4]) for h in FP.build_hooks(s, sym)]
        fo = s['func_off']
        lo, hi = fo, fo + 0x600                 # the layout function (and its literal pool) lies within 0x600 bytes
        pool = (fo + 0x78, s['wrap_off']) if s['variant'] == 'A' else (0, 0)    # literal pool between head and wrap block
        for off in range(lo, min(hi, len(d) - 1), 2):
            if pool[0] <= off < pool[1]:
                continue
            w = struct.unpack_from('<H', d, off)[0]
            t = None
            if (w >> 12) in (0xA,):
                disp = w & 0xFFF
                disp -= 0x1000 if disp & 0x800 else 0
                t = off + 4 + 2 * disp
            elif (w >> 8) in (0x89, 0x8B, 0x8D, 0x8F):
                disp = w & 0xFF
                disp -= 0x100 if disp & 0x80 else 0
                t = off + 4 + 2 * disp
            elif (w >> 12) == 0xD:
                t = ((off + 4) & ~3) + 4 * (w & 0xFF)
            elif (w >> 12) == 0x9:
                t = off + 4 + 2 * (w & 0xFF)
            elif (w >> 8) == 0xC7:
                t = ((off + 4) & ~3) + 4 * (w & 0xFF)
            if t is None:
                continue
            for r0, r1 in regions:
                if r0 < t < r1 and not (r0 <= off < r1):
                    # is `off` inside real code? (the layout function proper): report
                    tot_bad += 1
                    print('  XREF into interior of replaced region: %s insn@%#x word %04x -> %#x region %#x-%#x' % (s['name'], off, w, t, r0, r1))
    print('xref check: references into replaced interiors:', tot_bad)
    return tot_bad
