"""rfit_probe: run the real do_overlay / do_extra of build_patch on ONE source with the current DB and print the outcome.

    python -I -X utf8 tools/re/rfit_probe.py FLOW_PRG/AUTOSAVE.BIN [hw_relocate=on]

In memory only: nothing is written, no disc is built.  Prints failed / skipped counts, the notes (pool arena / slack) and the
time.  Used to learn what an overlay can absorb before a refit overlay is generated.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_patch as BP  # noqa: E402


def main(argv):
    source = argv[0]
    hw = argv[1].split('=')[1] if len(argv) > 1 else 'on'
    t0 = time.time()
    by_src = BP.load_tdb('translation')
    for a in argv[2:]:
        if a.startswith('overlay='):
            import refit
            m = refit.load_overlays(by_src, a.split('=', 1)[1], True)
            print('overlay applied: %d records' % len(m))
    recs = by_src[source]
    t1 = time.time()
    core = [r for r in recs if r.get('fmt') not in BP.textdb.EXTRA_FMTS]
    extra = [r for r in recs if r.get('fmt') in BP.textdb.EXTRA_FMTS]
    res = BP.Result()
    survey = BP.load_survey()
    if any(r.get('en') for r in core) or not any(r.get('en') for r in extra):
        BP.do_overlay(res, source, core, survey, True, True, 'dup', True)
    if any(r.get('en') for r in extra):
        BP.do_extra(res, source, extra, hw, 'dup', core)
    for f in res.files:
        print(f.iso, f.kind, 'applied', f.applied, 'failed', len(f.failed), 'skipped', len(f.skipped), 'in_place', f.in_place,
              'relocated', f.relocated)
        for n in f.notes:
            print('  note:', n)
        for fid, why in f.failed[:10]:
            print('  FAILED', fid, why[:120])
    print('load %.1fs, build %.1fs' % (t1 - t0, time.time() - t1))


if __name__ == '__main__':
    main(sys.argv[1:])
