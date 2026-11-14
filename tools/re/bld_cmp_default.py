"""bld_cmp_default: prove that the new build_patch flags do not change the default output.

    python -I -X utf8 tools/re/bld_cmp_default.py SNAPSHOT_TRANSLATION_DIR [--disc NAME_PREFIX]

Builds the patch set with the STANDARD flags (--repack on --share dup --append-safe --proportional-font on --texture-policy grow, money
format on) twice on the SAME input snapshot: with tools/build_patch.py as it is, and with an 'old-equivalent' copy of it made in memory
by removing the pass-through of the new options (prop_scale, money style, grow plan).  Compares the {iso path: bytes} dicts.  With --disc
the two discs are written to build/<prefix>_new and build/<prefix>_old and the 5 track files are compared byte for byte, then deleted.
"""
import importlib.util
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import build_patch as NEW   # noqa: E402


def make_old():
    src = open(os.path.join(ROOT, 'tools', 'build_patch.py'), encoding='utf8').read()
    for a, b in ((", glyphs=glyphs, prop_scale=prop_scale)", ", glyphs=glyphs)"),
                 ("decimal_d=decimal_d, style=style)", "decimal_d=decimal_d)"),
                 ("gp = grow_plan(source, img, survey, grow) if off is None else None", "gp = None")):
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    p = os.path.join(ROOT, 'build', 'bld_old_build_patch.py')
    open(p, 'w', encoding='utf8').write(src)
    spec = importlib.util.spec_from_file_location('bld_old_build_patch', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.HERE, m.ROOT = NEW.HERE, NEW.ROOT
    m.EXTRACTED, m.SURVEY = NEW.EXTRACTED, NEW.SURVEY
    return m


def run(mod, snap):
    t0 = time.time()
    res = mod.build_patches(os.path.join(snap), True, False, os.path.join(snap, 'font'), os.path.join(snap, 'members'),
                            os.path.join(snap, 'files'), None, True, 'dup', True, True, 'A', 'tail', True,
                            os.path.join(snap, 'textures'), 'grow', True, True, 'off')
    print('%s: %d patched files, digest %s, %.0fs' % (mod.__name__, len(res.patches), mod.patches_digest(res.patches), time.time() - t0), flush=True)
    return res


def main(argv):
    snap = os.path.abspath(argv[0])
    # the snapshot is a copy of translation/: its font / members / files / textures sub-directories travel with it
    old = make_old()
    rn = run(NEW, snap)
    ro = run(old, snap)
    same = rn.patches == ro.patches
    print('patch dicts identical: %s' % same)
    if not same:
        for k in sorted(set(rn.patches) | set(ro.patches)):
            if rn.patches.get(k) != ro.patches.get(k):
                print('  differs:', k)
    if '--disc' in argv:
        import discbuild
        pre = argv[argv.index('--disc') + 1]
        outs = {}
        for tag, r in (('new', rn), ('old', ro)):
            d = os.path.join(ROOT, 'build', '%s_%s' % (pre, tag))
            os.makedirs(d, exist_ok=True)
            discbuild.build_disc(r.patches, d, '%s_%s' % (pre, tag), ROOT, 'gap')
            outs[tag] = d
        ok = True
        for i in range(1, 6):
            a = os.path.join(outs['new'], '%s_new (Track %d).bin' % (pre, i))
            b = os.path.join(outs['old'], '%s_old (Track %d).bin' % (pre, i))
            import filecmp
            eq = filecmp.cmp(a, b, shallow=False)
            print('Track %d: %s (%d bytes)' % (i, 'identical' if eq else 'DIFFERENT', os.path.getsize(a)))
            ok = ok and eq
        for d in outs.values():
            shutil.rmtree(d, ignore_errors=True)
        print('tracks identical: %s' % ok)
        return 0 if ok and same else 1
    return 0 if same else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
