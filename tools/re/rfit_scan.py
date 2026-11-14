"""rfit_scan: inventory of short English forms that may exist only because a slot was small (names owner helper).

    python -I -X utf8 tools/re/rfit_scan.py OUT.tsv [--fmt hwptr|ptr|recarr|all]

One row per distinct (ja, en, fmt): number of records, number of overlays, min / max slot, `full` = en fills its slot
(len(en)+1 == slot) in at least one record, `abbr` = en ends with '.' .  Read-only.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main(argv):
    out = argv[0]
    want = 'hwptr'
    if '--fmt' in argv:
        want = argv[argv.index('--fmt') + 1]
    agg = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                en = r.get('en')
                if not en:
                    continue
                fmt = r.get('fmt') or 'ptr'
                if want != 'all' and fmt != want:
                    continue
                slot = r.get('slot') or r.get('max_bytes') or 0
                src = r['id'].rsplit('#', 1)[0]
                k = (r['ja'], en, fmt)
                a = agg.setdefault(k, {'n': 0, 'src': set(), 'lo': 9999, 'hi': 0, 'full': 0, 'hw': 0})
                a['n'] += 1
                a['src'].add(src)
                a['lo'] = min(a['lo'], slot)
                a['hi'] = max(a['hi'], slot)
                if len(en) + 1 >= slot:
                    a['full'] += 1
                if 'hwpool' in (r.get('ctx') or ''):
                    a['hw'] += 1
    rows = sorted(agg.items(), key=lambda kv: (kv[0][2], kv[1]['lo'], kv[0][0]))
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('fmt\tja\ten\tlen\tn\toverlays\tlo\thi\tfull\thwpool\n')
        for (ja, en, fmt), a in rows:
            fh.write('%s\t%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n' % (fmt, ja, en, len(en), a['n'], len(a['src']), a['lo'], a['hi'], a['full'], a['hw']))
    print('%d distinct (ja,en,fmt) rows -> %s' % (len(rows), out))


if __name__ == '__main__':
    main(sys.argv[1:])
