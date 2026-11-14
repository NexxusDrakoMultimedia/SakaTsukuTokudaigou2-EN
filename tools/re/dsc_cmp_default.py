"""dsc_cmp_default: prove the new discbuild writes the SAME bytes as the old one when no new option is used.

    python -I -X utf8 tools/re/dsc_cmp_default.py OLD_DISCBUILD.py DUMP_DIR [--grow]

OLD_DISCBUILD.py = a saved copy of tools/discbuild.py from before the dsc changes (build/dsc_discbuild_old.py);
DUMP_DIR = `build_patch.py --dry-run --dump DUMP_DIR` output (the changed files of the standard build).
Builds the same patch set (and with --grow: extra growing files so that relocation / gap / append paths run) with both
implementations into build/dsc_cmpA and build/dsc_cmpB, compares the five tracks, cue and gdi byte for byte, deletes both."""
import filecmp
import importlib.util
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import discbuild as NEW   # noqa: E402


def load_old(path):
    spec = importlib.util.spec_from_file_location('discbuild_old', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    old = load_old(sys.argv[1])
    dump = sys.argv[2]
    grow = '--grow' in sys.argv
    patches = {}
    for dp, _dn, fns in os.walk(dump):
        for fn in fns:
            full = os.path.join(dp, fn)
            iso = '/' + os.path.relpath(full, dump).replace(os.sep, '/')
            with open(full, 'rb') as f:
                patches[iso] = f.read()
    print('patch set: %d files, %d bytes' % (len(patches), sum(map(len, patches.values()))))
    if grow:
        patches['/DP3.INI'] = b'x' * 12000                              # 3 sectors: gap relocation
        patches['/FLOW_PRG/NEWS.BIN'] = patches.get('/FLOW_PRG/NEWS.BIN', b'') + b'\x00' * 40000   # grows: relocation
    res = {}
    for tag, mod in (('A', old), ('B', NEW)):
        out = os.path.join(ROOT, 'build', 'dsc_cmp' + tag)
        shutil.rmtree(out, ignore_errors=True)
        t = time.time()
        r = mod.build_disc(dict(patches), out, 'cmp', ROOT, 'gap')
        print('%s: %.1fs moves=%d rewritten=%d end=%d' % (tag, time.time() - t, len(r['moves']), r['sectors_rewritten'], r['new_end_lba']))
        res[tag] = (out, r)
    ok = True
    for fn in sorted(os.listdir(res['A'][0])):
        a, b = os.path.join(res['A'][0], fn), os.path.join(res['B'][0], fn)
        same = os.path.exists(b) and filecmp.cmp(a, b, shallow=False)
        print('  %-24s %s' % (fn, 'identical' if same else 'DIFFERENT'))
        ok &= same
    ok &= sorted(os.listdir(res['A'][0])) == sorted(os.listdir(res['B'][0]))
    ok &= res['A'][1]['moves'] == res['B'][1]['moves'] and res['A'][1]['sectors_rewritten'] == res['B'][1]['sectors_rewritten']
    for tag in 'AB':
        shutil.rmtree(res[tag][0], ignore_errors=True)
    print('RESULT: default output %s' % ('UNCHANGED (cmp identical)' if ok else 'CHANGED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
