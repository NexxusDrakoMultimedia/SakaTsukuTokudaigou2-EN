"""mny_budget.py : worst-case rendered width of every English `%m` text in the jp money style (docs/number-formats.md s4.6).

    python -I -X utf8 tools/re/mny_budget.py [--out build/mny/budget.tsv] [--worst 17] [--only-bad]

For every translation record whose English text contains `%m` the window limit comes from tools/winwidth.limits (the same rule
tools/transcheck.py enforces), each line is measured with `%m` replaced by a worst-case money text, in cells (one cell per glyph) and
in pixels (proportional font advance table, tools/pixelwidth.py), and the slack is printed: how many glyphs the money text may have in
that line.  The money text lengths of the jp style:
    TYPICAL = '13 Oku 1500 Man' (15)    the widest TV capital and a normal contract / transfer / facility amount
    REAL    = '999 Oku 9999 Man' (16)   the realistic cap (funds of a rich club); every `%m` record fits 16
    CAP     = '9999 Oku 9999 Man' (17)  V = 99,999,999 (10^8 - 1 Man): the cap literal found next to the money code of 6+ overlays
    INT     = '-214748 Oku 3648 Man' (20)  any int32 (never reached by the game)
A line with several `%m` is charged for every one of them.  A `%M` (compact money, flag 77) is charged with the compact form of the sample
('13 Oku 1500M', '999 Oku 9999M', '9999 Oku 9999M'): the same sample amount through `%M`.  Exit 0 always; the TSV is the report.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import translib as T          # noqa: E402
import winwidth as WW         # noqa: E402
import pixelwidth as PX       # noqa: E402

SAMPLES = collections.OrderedDict([('8 (old budget)', 'x' * 8), ('TYPICAL 15', '13 Oku 1500 Man'), ('REAL 16', '999 Oku 9999 Man'),
                                   ('CAP 17', '9999 Oku 9999 Man'), ('INT 20', '-214748 Oku 3648 Man')])


def compact(txt):
    """what the same amount prints through `%M` (tools/moneypatch.py COMPACT_FLAG): ' Man' -> 'M' behind an Oku part"""
    return txt.replace(' Man', 'M') if ' Oku ' in txt else txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tdb', default='translation')
    ap.add_argument('--out', default='build/mny/budget.tsv')
    ap.add_argument('--only-bad', action='store_true')
    a = ap.parse_args()
    db = T.load_db(T.resolve_path(a.tdb))
    import transwork as W
    aggs = W.aggregate(db)
    items = W.build_items(db, aggs)
    cat_of = {it['ja']: it['_cat'] for it in items}
    table = PX.get_table('on')
    rows = []
    for fi, li, r in db.records():
        en = r.get('en') or ''
        if ('%m' not in en and '%M' not in en) or r.get('skip'):
            continue
        lim = WW.limits(r['ja'], cat_of.get(r['ja'], 'dialogue'), T.source_of(r['id']), r.get('ctx') or '')
        if lim.max_cells is None:
            continue
        res = {}
        for lab, txt in SAMPLES.items():
            bad_c = bad_p = 0
            worst_line = ''
            for line in en.split('\n'):
                if '%m' not in line and '%M' not in line:
                    continue
                s = line.replace('%m', txt).replace('%M', compact(txt))
                c = T.cells_of_line(s)
                pc = PX.check_line(s, lim.max_cells, table)
                if c > lim.max_cells:
                    bad_c = max(bad_c, c - lim.max_cells)
                if not pc['ok']:
                    bad_p = max(bad_p, (pc['over'] + 11) // 12 or 1)
                    worst_line = line
            res[lab] = (bad_c, bad_p, worst_line)
        # slack: glyphs the money text may have in the worst line (cells, other glyphs counted at 1 cell)
        slack = 99
        for line in en.split('\n'):
            n = line.count('%m') + line.count('%M')
            if n:
                base = T.cells_of_line(line.replace('%m', '').replace('%M', ''))
                slack = min(slack, (lim.max_cells - base) // n)
        rows.append((r['id'], lim.cls, lim.max_cells, slack, res, en.replace('\n', '|')))
    out = T.resolve_path(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    hdr = ['id', 'window', 'cells', 'slack(glyphs per %m)'] + ['over cells @' + k for k in SAMPLES] + ['over px(12px cells) @' + k for k in SAMPLES] + ['en']
    nbad = collections.Counter()
    with open(out, 'w', encoding='utf8', newline='\n') as f:
        f.write('\t'.join(hdr) + '\n')
        for rid, cls, mc, slack, res, en in sorted(rows):
            for lab in SAMPLES:
                if res[lab][0] or res[lab][1]:
                    nbad[lab] += 1
            if a.only_bad and not any(res[l][0] or res[l][1] for l in SAMPLES if l != '8 (old budget)'):
                continue
            f.write('\t'.join([rid, cls, str(mc), str(slack)] + [str(res[l][0]) for l in SAMPLES] + [str(res[l][1]) for l in SAMPLES] + [en]) + '\n')
    print('%d records with %%m' % len(rows))
    for lab in SAMPLES:
        print('  %-16s records over their window (cells or pixels): %d' % (lab, nbad[lab]))
    print('wrote', out)


if __name__ == '__main__':
    main()
