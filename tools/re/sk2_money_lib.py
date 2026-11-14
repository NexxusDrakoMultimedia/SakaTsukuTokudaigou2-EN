"""sk2_money_lib.py : stage-2 skeptic fix.  The sprintf / shared-library money formats whose Oku / Man version is NOT wider than the
Japanese (same cell count, fits the old byte slot) are converted from western to the user decision (jp style):

    '%6d00万円'  Y%6dM   -> %6d00 Man      (ABROAD FIRE PLNUMSET SELNAT: 6 + 2 + 4 cells, the Japanese is 6 + 2 + 4)
    '%s万円'     Y%s0000 -> %s Man          (shared number library: 6 cells = 万円 is 4 cells, ' Man' is 4)
    '@R/%s万円@' @R/Y%s0000@ -> @R/%s Man@

NOT converted (3 cells wider than the Japanese, needs the screens): '%s億%s万円' (and the @R/ form), '%2d億%02d00万円', INVEST formats.

    python -I -X utf8 tools/re/sk2_money_lib.py [--apply]
Every edit is checked against the exact old English text and the exact Japanese text; the file is written atomically.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import translib as T          # noqa: E402

EDITS = {
    ('%6d00万円', 'Y%6dM'): '%6d00 Man',
    ('%s万円', 'Y%s0000'): '%s Man',
    ('@R/%s万円@', '@R/Y%s0000@'): '@R/%s Man@',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tdb', default='translation')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    db = T.load_db(T.resolve_path(a.tdb))
    changes = {}
    for fi, li, r in db.records():
        key = (r.get('ja'), r.get('en'))
        if key in EDITS:
            changes.setdefault(fi, {})[li] = (r['en'], EDITS[key])
            print('%s  %r -> %r  (max_bytes %s)' % (r['id'], r['en'], EDITS[key], r.get('max_bytes')))
    print('%d records' % sum(len(v) for v in changes.values()))
    if a.apply:
        for fi, edits in changes.items():
            f = db.files[fi]
            cur = T.load_db(T.resolve_path(a.tdb))
            cf = [x for x in cur.files if x.name == f.name][0]
            if not cf.plain or len(cf.recs) != len(f.recs):
                print('SKIP %s: file changed or not plain' % f.name)
                continue
            for li, (old, new) in edits.items():
                if cf.recs[li]['id'] != f.recs[li]['id'] or cf.recs[li].get('en') != old:
                    print('SKIP record %s: changed meanwhile' % f.recs[li]['id'])
                    continue
                cf.recs[li]['en'] = new
                cf.lines[li] = T.dump_record(cf.recs[li], cf.compact)
            T.write_atomic(cf.path, '\n'.join(cf.lines) + '\n')
            print('wrote', cf.path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
