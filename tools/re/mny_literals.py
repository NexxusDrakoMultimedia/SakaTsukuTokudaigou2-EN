"""mny_literals.py : English texts with a LITERAL western money amount (Y200M, 300 million yen, Y30K ...) -> the Oku / Man form of the
user decision (docs/number-formats.md s4.6).  Only the amounts change (and the line breaks of a line that no longer fits); every
replacement is checked against the exact old text, so a record that somebody edited meanwhile is skipped.

    python -I -X utf8 tools/re/mny_literals.py            # dry run
    python -I -X utf8 tools/re/mny_literals.py --apply    # write translation/*.jsonl (atomic per file)

NOT touched (they need the screen layout, listed in docs/number-formats.md s5): the sprintf formats `Y%2d%02dM`, `Y%6dM`, the shared
number library `Y%s%s0000` / `Y%s` and its `0円` piece `Y0`, `%d00M` / `%d0K` of GAME, the INVEST formats `Y%d.%04d%02dT` ...
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import translib as T          # noqa: E402
import winwidth as WW         # noqa: E402
import pixelwidth as PX       # noqa: E402
import mny_rewrap as RW       # noqa: E402

# id -> [(old text, new text)]   (substring replacements inside the English text)
EDITS = {
    'FLOW_PRG/EVENT.BIN#ce53c': [('@P/300 million yen@', '@P/3 Oku@')],
    'FLOW_PRG/EVENT.BIN#ce5d8': [('@P/100 million yen@', '@P/1 Oku@')],
    'FLOW_PRG/EVENT.BIN#e6474': [('Profit of Y200M', 'Profit of 2 Oku')],
    'FLOW_PRG/G_INCOME.BIN#28b50': [('Profit of Y200M', 'Profit of 2 Oku')],
    'FLOW_PRG/EVENT.BIN#e89bc': [('@P/Y200M@', '@P/2 Oku@')],
    'FLOW_PRG/HOMETOWN.BIN#4706b': [('Y990M.', '9 Oku 9000 Man.')],
    'FLOW_PRG/INVEST.BIN#ce22': [('@R/Y9,999M@', '@R/99 Oku 9900 Man@')],
    'FLOW_PRG/JSCEVENT.BIN#d783': [('is Y100M.', 'is 1 Oku.')],
}
for rid in ('GETREP.BIN#28bac', 'MON_INST.BIN#24358'):            # right-aligned 7 cell columns of the Japanese "  3万円"
    EDITS['FLOW_PRG/' + rid] = [('   Y30K', '  3 Man')]
for rid in ('GETREP.BIN#28bb4', 'MON_INST.BIN#24360'):
    EDITS['FLOW_PRG/' + rid] = [('   Y50K', '  5 Man')]
for rid in ('GETREP.BIN#28bbc', 'MON_INST.BIN#24368'):
    EDITS['FLOW_PRG/' + rid] = [('  Y100K', ' 10 Man')]
for rid in ('GETREP.BIN#28bc4', 'MON_INST.BIN#24370'):
    EDITS['FLOW_PRG/' + rid] = [('     Y0', '  0 Yen')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tdb', default='translation')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    db = T.load_db(T.resolve_path(a.tdb))
    import transwork as W
    cat_of = {it['ja']: it['_cat'] for it in W.build_items(db, W.aggregate(db))}
    table = PX.get_table('on')
    changes = {}
    seen = set()
    for fi, li, r in db.records():
        rid, en = r['id'], r.get('en') or ''
        edits = EDITS.get(rid)
        if rid.startswith('FLOW_PRG/MEETING.BIN#') and en.startswith('Y10M bonus'):       # 13 copies of the bonus menu
            edits = [('Y10M bonus', '1000 Man bonus')]
        if not edits:
            continue
        seen.add(rid)
        new = en
        for old, rep in edits:
            if old not in new:
                print('SKIP %s: %r not in the current text' % (rid, old))
                new = None
                break
            new = new.replace(old, rep)
        if new is None:
            continue
        lim = WW.limits(r['ja'], cat_of.get(r['ja'], 'dialogue'), T.source_of(rid), r.get('ctx') or '')
        if lim.max_cells is not None and not all(RW.fits(l, lim, table) for l in new.split('\n')):
            rw = RW.rewrap(new, lim, table)
            if rw is None:
                print('UNFIXED (does not fit %s): %s  %s' % (lim.cls, rid, new.replace('\n', '|')))
                continue
            new = rw
        changes.setdefault(fi, {})[li] = (en, new)
        print('%s\n    - %s\n    + %s' % (rid, en.replace('\n', '|'), new.replace('\n', '|')))
    miss = [k for k in EDITS if k not in seen]
    print('%d records to change, %d listed ids not found: %s' % (sum(len(v) for v in changes.values()), len(miss), miss))
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
