"""dsc_trial: build a trial disc from a build_patch --dump directory with the dsc options and print verify_disc's report.

    python -I -X utf8 tools/re/dsc_trial.py DUMP_DIR [--dedupe] [--add-readme] [--keep]

Writes build/dsc_trial (deleted afterwards unless --keep).  DUMP_DIR comes from `build_patch.py --dry-run --dump DUMP_DIR`."""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import discbuild as D   # noqa: E402
import verify_disc as V   # noqa: E402


def main():
    dump = sys.argv[1]
    patches = {}
    for dp, _dn, fns in os.walk(dump):
        for fn in fns:
            full = os.path.join(dp, fn)
            with open(full, 'rb') as f:
                patches['/' + os.path.relpath(full, dump).replace(os.sep, '/')] = f.read()
    spec = D.DiscSpec(patches, dedupe='--dedupe' in sys.argv)
    if '--add-readme' in sys.argv:
        spec.add_file('/README.TXT', b'SakaTsuku2 English patch trial\r\n' * 30)
    out = os.path.join(ROOT, 'build', 'dsc_trial')
    shutil.rmtree(out, ignore_errors=True)
    t = time.time()
    r = D.build_disc(spec, out, 'trial', ROOT)
    print('build %.1fs: rewritten %d, moves %d, added %s, end %d, free %d, dedupe groups %d' % (
        time.time() - t, r['sectors_rewritten'], len(r['moves']), r['added'], r['new_end_lba'], r['free_sectors'], len(r['dedupe'])))
    t = time.time()
    rep = V.verify_disc(out, 'trial', ROOT, expect=patches, rewritten=r['rewritten_lbas'])
    print(rep.text())
    print('verify %.1fs' % (time.time() - t))
    if '--keep' not in sys.argv:
        shutil.rmtree(out, ignore_errors=True)
    return 0 if rep.ok else 1


if __name__ == '__main__':
    sys.exit(main())
