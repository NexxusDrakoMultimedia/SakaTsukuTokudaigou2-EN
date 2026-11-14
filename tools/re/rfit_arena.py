"""rfit_arena: baseline of every overlay with hw / record-array strings (in memory, real build code, nothing written).

    python -I -X utf8 tools/re/rfit_arena.py OUT.tsv

One row per source: translated hwptr / recarr / other records, failed and skipped counts with the current DB and
`--hw-relocate on --share dup`, and the pool arena capacity / used / slack of the hw pool.  The slack is what a refit can use.
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_patch as BP  # noqa: E402

NOTE = re.compile(r'hw pool: (\d+) strings \((\d+) in place, (\d+) relocated\), arena (\d+) bytes, used (\d+), slack (\d+)')


def main(argv):
    out = argv[0]
    by_src = BP.load_tdb('translation')
    survey = BP.load_survey()
    rows = []
    for source in sorted(by_src):
        recs = by_src[source]
        if BP.handler_for(source) != 'overlay':
            continue
        core = [r for r in recs if r.get('fmt') not in BP.textdb.EXTRA_FMTS]
        extra = [r for r in recs if r.get('fmt') in BP.textdb.EXTRA_FMTS]
        if not any(r.get('en') for r in recs):
            continue
        t0 = time.time()
        res = BP.Result()
        if any(r.get('en') for r in core) or not any(r.get('en') for r in extra):
            BP.do_overlay(res, source, core, survey, True, True, 'dup', True)
        if any(r.get('en') for r in extra):
            BP.do_extra(res, source, extra, 'on', 'dup', core)
        failed = sum(len(f.failed) for f in res.files)
        skipped = sum(len(f.skipped) for f in res.files)
        notes = [n for f in res.files for n in f.notes]
        m = None
        for n in notes:
            m = NOTE.search(n) or m
        hw = sum(1 for r in extra if r.get('fmt') == 'hwptr' and r.get('en'))
        ra = sum(1 for r in extra if r.get('fmt') == 'recarr' and r.get('en'))
        co = sum(1 for r in core if r.get('en'))
        rows.append((source, hw, ra, co, failed, skipped, m.groups() if m else ('', '', '', '', '', ''), time.time() - t0))
        print(source, hw, ra, co, failed, skipped, m.group(6) if m else '-', '%.1fs' % (time.time() - t0), flush=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('source\thw\trecarr\tcore\tfailed\tskipped\tstrings\tin_place\trelocated\tarena\tused\tslack\n')
        for s, hw, ra, co, fa, sk, g, _t in rows:
            fh.write('\t'.join([s, str(hw), str(ra), str(co), str(fa), str(sk)] + list(g)) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
