"""Self-test of the build_patch.py flags added by the build owner (bld): --grow-overlays, --prop-scale, --money-style, --refit,
the texture-policy error message and the argument validation.   Run:  python -I -X utf8 tools/test_bldflags.py     (~20 s)

 1. grow_plan eligibility (survey class bss, exclusion list, caps, `_end` word check); grow 0 = no plan.
 2. --grow-overlays mechanics on the real FLOW_PRG/ABROAD.BIN (BSS overlay) with strings too long for the pools: grow 0 leaves them
    Japanese (FAILED) and the image byte-identical; grow N pads with zeros up to the old `_end`, appends, raises the `_end` word to
    base + new size, every translated pointer resolves; a cap below the need leaves the repack result and says so.
 3. --prop-scale: only the cave bytes of 1ST_READ.BIN differ from the default (other files identical); validation errors.
 4. --money-style: jp (default) vs western: same files and sizes, formatter cave + the hook displacement differ; unknown style raises.
 5. --refit: the real tools/refit.py on a temporary <tdb>/refit directory: en replaced in memory; forces hw-relocate on; bad overlay = PipelineError.
 6. texture policy: an over-slot texture produces ONE PipelineError naming file, texture id and bytes over (no traceback).
Nothing is written outside the temp directory; no disc is built.
"""
import os
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(ROOT)
import build_patch as BP      # noqa: E402
import textdb                 # noqa: E402
import textrepack as R        # noqa: E402

RESULTS = []


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    print(('ok   ' if cond else 'FAIL ') + msg, flush=True)


def raises(fn, text=None):
    try:
        fn()
    except BP.PipelineError as e:
        return text is None or text in str(e)
    return False


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def cstr(d, o):
    return d[o:d.index(b'\0', o)]


# ------------------------------------------------------------------ 1 + 2
def test_grow():
    survey = BP.load_survey()
    src = 'FLOW_PRG/ABROAD.BIN'
    img = textdb.load_image(src)
    check(BP.grow_plan(src, img, survey, 0) is None, 'grow 0: no plan (default unchanged)')
    gp = BP.grow_plan(src, img, survey, 4096)
    check(gp is not None and gp[2] == 4096 and gp[1] >= img.base + img.size and u32(img.data, gp[0]) == gp[1],
          'ABROAD (BSS overlay): plan with `_end` word %s' % (gp and hex(gp[1])))
    check(BP.grow_plan(src, img, survey, 10 ** 9) is None or BP.grow_plan(src, img, survey, BP.GROW_MAX)[2] == BP.GROW_MAX, 'cap = GROW_MAX')
    for name in ('GAME.BIN', 'ESTABLIS.BIN', 'MOVIE.BIN', 'LOADBAR.BIN', 'COMM.BIN'):
        check(BP.grow_plan('FLOW_PRG/' + name, img, survey, 4096) is None, '%s is excluded' % name)
    check(BP.grow_plan('ATFIRST/HELP.BIN', img, survey, 4096) is None, 'ATFIRST copies are never grown')
    nobss = [k for k, d in survey.items() if d.get('class', '').startswith('no-bss')]
    if nobss:
        im2 = textdb.load_image('FLOW_PRG/' + nobss[0])
        check(BP.grow_plan('FLOW_PRG/' + nobss[0], im2, survey, 4096) is None, 'no-bss overlay: left to --append-safe proper')
    strs, ptrs, _x = textdb.extract_image(img)
    ext = (strs, ptrs, _x)
    big = [s for s in strs if R.is_movable(s) and len(s.raw) >= 8 and s.refs][:12]
    recs = []
    for i, s in enumerate(big):
        recs.append({'id': '%s#%x' % (src, s.off), 'ja': textdb.decode_text(s.raw), 'en': (chr(65 + i) + 'bcdefgh') * 400})
    # 12 distinct strings of 3200 bytes: far above the pool slack of this overlay
    res0 = BP.Result()
    BP.do_overlay(res0, src, recs, survey, True, True, 'none', True, 0)
    check(res0.files[0].failed and not res0.files[0].appended, 'grow 0 + append-safe: BSS overlay refuses (%d FAILED)' % len(res0.files[0].failed))
    base_patch = res0.patches.get('/' + src)
    check(base_patch is None or len(base_patch) == img.size, 'grow 0: image size unchanged')
    res1 = BP.Result()
    BP.do_overlay(res1, src, recs, survey, True, True, 'none', True, 65536)
    rep = res1.files[0]
    new = res1.patches.get('/' + src)
    check(new is not None and not rep.failed, 'grow 65536: every string placed, none FAILED')
    if new is None:
        return
    old_end = gp[1]
    padded = (old_end - img.base + 3) & ~3
    check(len(new) > padded and u32(new, gp[0]) == img.base + len(new), '`_end` word raised to base + new size (%#x)' % u32(new, gp[0]))
    check(new[img.size:padded] == bytes(padded - img.size), 'BSS pad %d bytes is all zero' % (padded - img.size))
    check(len(new) - padded <= 65536 and (len(new) % 4) == 0, 'appended %d bytes (cap respected, 4-aligned)' % (len(new) - padded))
    ok = 0
    for r, s in zip(recs, big):
        for w in s.refs:
            a = u32(new, w)
            if a - img.base >= 0 and cstr(new, a - img.base).decode('cp932') == r['en']:
                ok += 1
                break
    check(ok == len(recs), 'every translated string is reachable through its pointer (%d/%d)' % (ok, len(recs)))
    other = [w for w in range(0, img.size - 3, 4) if u32(new, w) != u32(img.data, w)]
    check(len(other) > 0, 'only pointer / text words differ in the image part')
    res2 = BP.Result()
    BP.do_overlay(res2, src, recs, survey, True, True, 'none', True, 64)
    n2 = res2.files[0]
    check(any('limit 64' in n for n in n2.notes) and n2.failed and len(res2.patches.get('/' + src, img.data)) == img.size,
          'cap below the need: left as repacked and reported')


# ------------------------------------------------------------------ 3 + 4 + 5
def empty_tdb(tmp):
    d = os.path.join(tmp, 'tdb')
    os.makedirs(d, exist_ok=True)
    return d


def test_flags(tmp):
    tdb = empty_tdb(tmp)
    nt = os.path.join(tmp, 'notex')
    os.makedirs(nt, exist_ok=True)       # an empty textures dir: these tests must not depend on the art owner's live textures
    # validation (cheap)
    check(raises(lambda: BP.build_patches(tdb, prop_font=False, prop_scale=True), '--proportional-font on'), '--prop-scale needs the proportional font')
    check(raises(lambda: BP.build_patches(tdb, prop_font=True, prop_scale=True, prop_place='gap1'), 'tail'), '--prop-scale refuses the gap1 placement')
    check(raises(lambda: BP.build_patches(tdb, grow_overlays=100), '--append-safe'), '--grow-overlays needs --append-safe')
    check(raises(lambda: BP.build_patches(tdb, append_safe=True, grow_overlays=-1), 'between'), '--grow-overlays range')
    check(raises(lambda: BP.build_patches(tdb, money_fmt=True, money_style='decimal'), 'money style'), 'unknown money style')
    # prop-scale
    a = BP.build_patches(tdb, prop_font=True, prop_glyphs=True, textures_dir=nt)
    b = BP.build_patches(tdb, prop_font=True, prop_glyphs=True, prop_scale=True, textures_dir=nt)
    check(sorted(a.patches) == sorted(b.patches), 'prop-scale touches the same %d files' % len(a.patches))
    diff = sorted(k for k in a.patches if a.patches[k] != b.patches[k])
    check(diff == ['/1ST_READ.BIN'], 'only 1ST_READ.BIN differs: %s' % diff)
    ofs = [i for i in range(len(a.patches['/1ST_READ.BIN'])) if a.patches['/1ST_READ.BIN'][i] != b.patches['/1ST_READ.BIN'][i]]
    lo, hi = 0x8c299800 - 0x8c010000, 0x8c299900 - 0x8c010000
    check(ofs and lo <= min(ofs) and max(ofs) < hi, 'differences lie in the cave reserve %#x..%#x (%d bytes)' % (lo, hi, len(ofs)))
    check(any('prop-scale' in n for f in b.files for n in f.notes), 'summary note mentions --prop-scale')
    # money style
    j = BP.build_patches(tdb, money_fmt=True, money_style='jp', textures_dir=nt)
    w = BP.build_patches(tdb, money_fmt=True, money_style='western', textures_dir=nt)
    d0 = BP.build_patches(tdb, money_fmt=True, textures_dir=nt)
    check(j.patches == d0.patches, 'default money style == jp')
    nd = {k: sum(1 for x, y in zip(j.patches[k], w.patches[k]) if x != y) for k in j.patches if k in w.patches}
    check(sorted(j.patches) == sorted(w.patches) and all(len(j.patches[k]) == len(w.patches[k]) for k in j.patches)
          and nd['/1ST_READ.BIN'] > 100 and all(n <= 64 for k, n in nd.items() if k != '/1ST_READ.BIN'),
          'jp vs western: same files and sizes; the formatter in 1ST_READ.BIN (%d bytes) and <= 64 patch bytes per overlay (hooks + the mn6 compact-form panel sites; was 4 before mn6 added them, stage 8b) differ' % nd['/1ST_READ.BIN'])
    check(any('jp style' in n for n in j.notes) and any('western style' in n for n in w.notes), 'summary names the style')
    # refit: the real tools/refit.py on a temporary overlay directory <tdb>/refit
    import refit
    rdir = os.path.join(tdb, 'refit')
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, 'DPETC__MESSAGE.INI.jsonl'), 'w', encoding='utf8') as f:
        f.write('{"id":"DPETC/MESSAGE.INI#1","ja":"あ","en":"Refit text","why":"test","cls":"other"}' + chr(10) +
                '{"id":"NOPE/X.BIN#0","en":"x","why":"test"}' + chr(10))
    by = {'DPETC/MESSAGE.INI': [{'id': 'DPETC/MESSAGE.INI#1', 'ja': 'あ', 'en': 'old', 'max_bytes': 40, 'refs': 1, 'ctx': 'ptr'}]}
    res = BP.Result()
    rep = BP.apply_refit(by, tdb, res)
    check(len(rep.modified) == 1 and by['DPETC/MESSAGE.INI'][0]['en'] == 'Refit text' and len(rep.skipped) == 1,
          'apply_refit (real tools/refit.py) replaces en in memory, skips the unknown id')
    check(any(n.startswith('refit:') for n in res.notes), 'refit summary is in the build notes')
    r = BP.build_patches(tdb, refit=True, textures_dir=nt)
    check(any('hw-relocate forced on' in n for n in r.notes), '--refit on forces --hw-relocate on')
    r = BP.build_patches(tdb, refit=True, hw_relocate='force', textures_dir=nt)
    check(not any('forced on' in n for n in r.notes), '--hw-relocate force is kept')
    with open(os.path.join(rdir, 'DPETC__MESSAGE.INI.jsonl'), 'w', encoding='utf8') as f:
        f.write('{"id":"x"}' + chr(10))
    check(raises(lambda: BP.build_patches(tdb, refit=True, textures_dir=nt), 'refit overlays'), 'a malformed overlay stops the build with a PipelineError')


# ------------------------------------------------------------------ 8 (open font): --open-font
def test_open_font(tmp):
    import fontpatch as FPT
    import font as F
    import openfont
    import pixelwidth
    tdb = os.path.join(tmp, 'tdb_open')          # not the directory of test_flags (it ends with a malformed refit overlay)
    os.makedirs(tdb, exist_ok=True)
    nt = os.path.join(tmp, 'notex')
    os.makedirs(nt, exist_ok=True)
    check(raises(lambda: BP.build_patches(tdb, open_font=True, textures_dir=nt), '--proportional-font on'), '--open-font on needs --proportional-font on (library)')
    check(raises(lambda: BP.build_patches(tdb, prop_font=True, prop_glyphs=False, open_font=True, textures_dir=nt), '--proportional-font on'),
          '--open-font on is refused with the control table (glyphs untouched)')
    base = BP.build_patches(tdb, prop_font=True, prop_glyphs=True, textures_dir=nt)
    off = BP.build_patches(tdb, prop_font=True, prop_glyphs=True, open_font=False, textures_dir=nt)
    on = BP.build_patches(tdb, prop_font=True, prop_glyphs=True, open_font=True, textures_dir=nt)
    check(base.patches == off.patches and BP.patches_digest(base.patches) == BP.patches_digest(off.patches),
          '--open-font off: byte-identical to the build without the keyword (%d files)' % len(off.patches))
    check(not any('open' in n.lower() and 'font' in n.lower() for n in off.notes + [x for f in off.files for x in f.notes]), 'off: no open-font note')
    # the off build is today's build: its font copies are what the unchanged proportional_font makes
    orig = F.Font(BP.read_extracted('FONT.BIN'))
    ref, ref_table = FPT.proportional_font(BP.read_extracted('FONT.BIN'), orig.half())
    check(off.patches['/FONT.BIN'] == ref, 'off: /FONT.BIN = fontpatch.proportional_font (original art, shifted)')
    check(sorted(on.patches) == sorted(off.patches), 'on touches the same %d files' % len(on.patches))
    diff = sorted(k for k in on.patches if on.patches[k] != off.patches[k])
    check(diff == ['/1ST_READ.BIN', '/ATFIRST/FONT.BIN', '/FONT.BIN'], 'only the two FONT.BIN copies and 1ST_READ.BIN differ: %s' % diff)
    ofs = [i for i in range(len(on.patches['/1ST_READ.BIN'])) if on.patches['/1ST_READ.BIN'][i] != off.patches['/1ST_READ.BIN'][i]]
    lo, hi = 0x8c299900 - 0x8c010000, 0x8c299a00 - 0x8c010000
    check(ofs and lo <= min(ofs) and max(ofs) < hi, '1ST_READ.BIN differs only in the 256 byte advance table %#x..%#x (%d bytes)' % (lo, hi, len(ofs)))
    glyphs, tab = openfont.load()
    k = on.patches['/1ST_READ.BIN']
    check(k[lo:hi] == tab, 'the table in 1ST_READ.BIN is the committed advance table (space %d px)' % tab[0x20])
    for cp in ('/FONT.BIN', '/ATFIRST/FONT.BIN'):
        h = F.Font(on.patches[cp]).half()
        o = F.Font(off.patches[cp]).half()
        check(all(h[F.half_index(b)] == glyphs[b] for b in glyphs) and all(h[i] == o[i] for i in range(160) if i not in [F.half_index(b) for b in glyphs]),
              '%s: the 94 slots are the open glyphs, everything else equals the off build' % cp)
        check(len(on.patches[cp]) == len(off.patches[cp]), '%s: size unchanged' % cp)
    check(any('Roboto' in n for f in on.files for n in f.notes), 'on: the FONT.BIN report names the font')
    check(pixelwidth.get_table('on')[0x20] == 12, 'the width switch of the build is restored after it (profile on = old table)')
    # refit / lint measure with the new table while the build runs
    import refit
    seen = {}
    orig_apply = BP.apply_refit

    def spy(by, tdb_, res, *a, **kw):
        seen['space'] = pixelwidth.get_table()[0x20]
        seen['W'] = pixelwidth.line_px('WW')[0]
        return orig_apply(by, tdb_, res, *a, **kw)
    BP.apply_refit = spy
    try:
        BP.build_patches(tdb, prop_font=True, prop_glyphs=True, open_font=True, refit=True, textures_dir=nt)
        s_on = dict(seen)
        seen.clear()
        BP.build_patches(tdb, prop_font=True, prop_glyphs=True, open_font=False, refit=True, textures_dir=nt)
    finally:
        BP.apply_refit = orig_apply
    check(s_on.get('space') == tab[0x20] and seen.get('space') == 12, 'apply_refit sees the open table (space %s) with the flag on and the old one (%s) off' % (s_on.get('space'), seen.get('space')))
    # command line
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = BP.main(['--tdb', tdb, '--textures-dir', nt, '--open-font', 'on', '--dry-run'])
    check(rc == 1 and '--open-font on needs --proportional-font on' in err.getvalue(), '--open-font on without --proportional-font on: clear error, exit 1')
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = BP.main(['--tdb', tdb, '--textures-dir', nt, '--proportional-font', 'on', '--open-font', 'on', '--refit', 'off', '--dry-run'])
    check(rc == 0 and '--open-font on' in out.getvalue(), '--proportional-font on --open-font on works (dry run) and the flags line says so')
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = BP.main(['--tdb', tdb, '--textures-dir', nt, '--proportional-font', 'on', '--refit', 'off', '--dry-run'])
    check(rc == 0 and 'open-font' not in out.getvalue(), 'default (off): the flags line is unchanged')


# ------------------------------------------------------------------ 6
def test_texture_error(tmp):
    import texinject as T
    tdir = os.path.join(tmp, 'tex', 'ATFIRST', 'HELP.DAT')
    os.makedirs(tdir)
    pvr = T.extract_pvr('ATFIRST/HELP.DAT', '#0')
    with open(os.path.join(tdir, '#0.pvr'), 'wb') as f:
        f.write(pvr)
    orig = T.inject

    def boom(*a, **k):
        raise T.FitError('record #0: repainted data packs to 9000 bytes, slot is 4000', 9000, 4000)
    T.inject = boom
    try:
        for pol in ('exact', 'grow'):
            res = BP.Result()
            try:
                BP.apply_textures(res, os.path.join(tmp, 'tex'), pol)
                check(False, 'over-slot texture raises (%s)' % pol)
            except BP.PipelineError as e:
                m = str(e)
                check('ATFIRST/HELP.DAT' in m and '#0' in m and '5000 bytes over' in m and '--texture-policy %s' % pol in m,
                      'error names file, texture and overrun (%s)' % pol)
    finally:
        T.inject = orig
    res = BP.Result()
    BP.apply_textures(res, os.path.join(tmp, 'tex'), 'exact')
    check(res.files and res.files[0].kind == 'texture', 'unmodified texture still injects under policy exact')


# ------------------------------------------------------------------ 7 (stage 8b): command-line defaults, flag checks, --strict exit code
def test_cli(tmp):
    import contextlib
    import io
    orig = BP.build_patches
    seen = {}

    def fake(*a, **k):
        seen['args'] = a
        seen['kw'] = k
        res = BP.Result()
        fr = BP.FileReport('/FLOW_PRG/X.BIN', 'overlay')
        if seen.get('fail'):
            fr.failed.append(('FLOW_PRG/X.BIN#1', 'does not fit'))
        res.files.append(fr)
        return res
    BP.build_patches = fake

    def run(argv, fail=False):
        seen['fail'] = fail
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = BP.main(argv + ['--dry-run'])
        return rc, out.getvalue(), err.getvalue()
    try:
        rc, out, err = run(['--proportional-font', 'on'])
        a = seen['args']
        check(rc == 0 and a[-4] is True and a[-2] is True and a[-1] is True, 'defaults: refit, align-fix and tag-fix are ON on the command line (rc %d)' % rc)
        check('--refit on --align-fix on --tag-fix on' in out, 'the "flags:" line prints the effective flags')
        k = seen['kw']
        check(k.get('crowd_fix') is True and k.get('bcast_speed') == '1.9' and k.get('scout_fix') is True,
              'defaults: --crowd-fix on and --bcast-speed 1.9 (and --scout-fix on) reach build_patches')
        check('--crowd-fix on --bcast-speed 1.9' in out, 'the "flags:" line prints --crowd-fix on --bcast-speed 1.9')
        rc, out, err = run(['--proportional-font', 'on', '--crowd-fix', 'off', '--bcast-speed', 'off'])
        check(rc == 0 and seen['kw'].get('crowd_fix') is False and seen['kw'].get('bcast_speed') == 'off' and '--crowd-fix off --bcast-speed off' in out,
              '--crowd-fix off / --bcast-speed off work and are printed')
        for sp in ('1.7', '2.2'):
            rc, out, err = run(['--proportional-font', 'on', '--bcast-speed', sp])
            check(rc == 0 and seen['kw'].get('bcast_speed') == sp and ('--bcast-speed %s' % sp) in out, '--bcast-speed %s is accepted and printed' % sp)
        try:
            rc = run(['--proportional-font', 'on', '--bcast-speed', '3.0'])[0]
        except SystemExit as e:
            rc = e.code
        check(rc == 2, '--bcast-speed 3.0 is refused by the argument parser (exit 2)')
        rc, out, err = run(['--proportional-font', 'on'])
        check(rc == 0 and seen['kw'].get('lin_center') is True and '--lin-center on' in out, 'default: --lin-center on reaches build_patches and the flags line')
        rc, out, err = run(['--proportional-font', 'on', '--open-font', 'on'])
        check(rc == 0 and seen['kw'].get('lin_center') is True and seen['kw'].get('open_font') is True, '--lin-center is on by default with --open-font on')
        rc, out, err = run(['--proportional-font', 'on', '--lin-center', 'off'])
        check(rc == 0 and seen['kw'].get('lin_center') is False and '--lin-center off' in out, '--lin-center off works and is printed')
        rc, out, err = run([])
        check(rc == 0 and seen['kw'].get('lin_center') is False and '--lin-center off' in out, 'bare command line: --lin-center defaults off')
        rc, out, err = run(['--proportional-font', 'off', '--lin-center', 'on'])
        check(rc == 1 and 'ERROR' in err and '--proportional-font on' in err, '--lin-center on is refused without --proportional-font on')
        rc, out, err = run(['--proportional-font', 'control', '--lin-center', 'on'])
        check(rc == 1 and 'ERROR' in err, '--lin-center on is refused with --proportional-font control')
        rc, out, err = run(['--proportional-font', 'on', '--prop-font-place', 'gap1', '--lin-center', 'on'])
        check(rc == 1 and 'tail' in err, '--lin-center on is refused with --prop-font-place gap1')
        rc, out, err = run(['--proportional-font', 'on', '--prop-font-place', 'gap1'])
        check(rc == 0 and seen['kw'].get('lin_center') is False, 'gap1 placement: --lin-center defaults off (no error)')
        rc, out, err = run(['--proportional-font', 'on'])
        check(rc == 0 and seen['kw'].get('cell_prop') is True and '--lin-center on --cell-prop on --money-format' in out, 'default: --cell-prop on reaches build_patches and the flags line')
        rc, out, err = run(['--proportional-font', 'on', '--open-font', 'on'])
        check(rc == 0 and seen['kw'].get('cell_prop') is True, '--cell-prop is on by default with --open-font on')
        rc, out, err = run(['--proportional-font', 'on', '--cell-prop', 'off'])
        check(rc == 0 and seen['kw'].get('cell_prop') is False and '--cell-prop off' in out, '--cell-prop off works and is printed')
        rc, out, err = run([])
        check(rc == 0 and seen['kw'].get('cell_prop') is False and '--cell-prop off' in out, 'bare command line: --cell-prop defaults off')
        for argv, word in ((['--proportional-font', 'off'], '--proportional-font on'), (['--proportional-font', 'control'], '--proportional-font on'),
                           (['--proportional-font', 'on', '--prop-font-place', 'gap1'], 'tail')):
            rc, out, err = run(argv + ['--cell-prop', 'on'])
            check(rc == 1 and 'ERROR' in err and '--cell-prop' in err and word in err, '--cell-prop on is refused: %s' % ' '.join(argv))
        rc, out, err = run(['--proportional-font', 'on', '--prop-font-place', 'gap1'])
        check(rc == 0 and seen['kw'].get('cell_prop') is False, 'gap1 placement: --cell-prop defaults off (no error)')
        rc, out, err = run(['--proportional-font', 'on'])
        check(rc == 0 and seen['kw'].get('clip_lead_space') is True and '--clip-lead-space on' in out, 'default: --clip-lead-space follows --cell-prop (on), reaches build_patches and the flags line')
        rc, out, err = run(['--proportional-font', 'on', '--open-font', 'on'])
        check(rc == 0 and seen['kw'].get('clip_lead_space') is True, '--clip-lead-space is on by default with --open-font on')
        rc, out, err = run(['--proportional-font', 'on', '--clip-lead-space', 'off'])
        check(rc == 0 and seen['kw'].get('clip_lead_space') is False and seen['kw'].get('cell_prop') is True and '--clip-lead-space off' in out, '--clip-lead-space off works (trailing blank rule) and is printed')
        rc, out, err = run(['--proportional-font', 'on', '--cell-prop', 'off'])
        check(rc == 0 and seen['kw'].get('clip_lead_space') is False and '--clip-lead-space off' in out, '--cell-prop off: --clip-lead-space defaults off (old trailing blank rule)')
        rc, out, err = run([])
        check(rc == 0 and seen['kw'].get('clip_lead_space') is False and '--clip-lead-space off' in out, 'bare command line: --clip-lead-space defaults off')
        for argv in (['--proportional-font', 'on', '--cell-prop', 'off'], ['--proportional-font', 'off'], ['--proportional-font', 'control'],
                     ['--proportional-font', 'on', '--prop-font-place', 'gap1']):
            rc, out, err = run(argv + ['--clip-lead-space', 'on'])
            check(rc == 1 and 'ERROR' in err and '--clip-lead-space' in err and '--cell-prop' in err, '--clip-lead-space on is refused without --cell-prop on: %s' % ' '.join(argv))
        check(raises(lambda: orig(clip_lead_space=True, cell_prop=False), '--cell-prop'), 'build_patches(clip_lead_space=True) without cell_prop is refused')
        rc, out, err = run(['--proportional-font', 'on'])
        check(rc == 0 and seen['kw'].get('small_prop') is False and '--small-prop' not in out, '--small-prop is OFF by default and absent from the flags line')
        rc, out, err = run(['--proportional-font', 'on', '--small-prop', 'on'])
        check(rc == 0 and seen['kw'].get('small_prop') is True and '--small-prop on' in out, '--small-prop on reaches build_patches and the flags line')
        for argv in (['--proportional-font', 'off'], ['--proportional-font', 'control'], ['--proportional-font', 'on', '--prop-font-place', 'gap1'],
                     ['--proportional-font', 'on', '--prop-font-variants', 'ABC']):
            rc, out, err = run(argv + ['--small-prop', 'on'])
            check(rc == 1 and 'ERROR' in err and '--small-prop' in err, '--small-prop on is refused: %s' % ' '.join(argv))
        rc, out, err = run(['--proportional-font', 'on', '--refit', 'off', '--align-fix', 'off', '--tag-fix', 'off'])
        a = seen['args']
        check(rc == 0 and a[-4] is False and a[-2] is False and a[-1] is False, '--refit off / --align-fix off / --tag-fix off still work')
        for argv, word in ((['--proportional-font', 'off'], '--proportional-font on'), (['--proportional-font', 'control'], '--proportional-font on'),
                           (['--proportional-font', 'on', '--prop-font-variants', 'ABC'], 'variants A'),
                           (['--proportional-font', 'on', '--prop-font-place', 'gap1'], 'tail')):
            rc, out, err = run(argv + ['--align-fix', 'on'])
            check(rc == 1 and word in err and 'ERROR' in err, '--align-fix on is refused with a clear error: %s' % ' '.join(argv))
            rc, out, err = run(argv)
            check(rc == 0 and '--align-fix off' in out, 'without --align-fix the default falls back to off (no error): %s' % ' '.join(argv))
            rc, out, err = run(argv + ['--align-fix', 'off'])
            check(rc == 0, 'the same combination works with --align-fix off: %s' % ' '.join(argv))
        rc, out, err = run([])
        check(rc == 0 and '--align-fix off' in out, 'a bare command line (no --proportional-font) works: align-fix defaults off')
        rc, out, err = run(['--proportional-font', 'on'], fail=True)
        check(rc == 0, 'without --strict a failed string still exits 0 (summary says failed 1)')
        rc, out, err = run(['--proportional-font', 'on', '--strict'], fail=True)
        check(rc == 2 and 'failed 1' in out and '--strict' in err, '--strict: a failed string exits 2 and says so on stderr')
        rc, out, err = run(['--proportional-font', 'on', '--strict'])
        check(rc == 0, '--strict with nothing failed exits 0')
    finally:
        BP.build_patches = orig
    # library keywords
    check(raises(lambda: BP.build_patches(empty_tdb(tmp), small_prop=True), '--proportional-font on'), 'build_patches(small_prop=True) without the proportional font is refused')
    check(raises(lambda: BP.build_patches(empty_tdb(tmp), prop_font=True, small_prop=True, prop_variants='ABC'), 'variants A'), 'build_patches(small_prop=True) refuses variants ABC')
    check(raises(lambda: BP.build_patches(empty_tdb(tmp), align_fix=True), '--proportional-font on'), 'build_patches(align_fix=True) without the proportional font is refused')
    check(raises(lambda: BP.build_patches(empty_tdb(tmp), prop_font=True, align_fix=True, prop_variants='ABC'), 'variants A'), 'build_patches(align_fix=True) refuses variants ABC')


def main():
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='bldflags_', dir=os.path.join(ROOT, 'build')) as tmp:
        test_grow()
        test_flags(tmp)
        test_texture_error(tmp)
        test_open_font(tmp)
        test_cli(tmp)
    bad = [m for ok, m in RESULTS if not ok]
    print('%d checks, %d failed, %.1fs' % (len(RESULTS), len(bad), time.time() - t0))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
