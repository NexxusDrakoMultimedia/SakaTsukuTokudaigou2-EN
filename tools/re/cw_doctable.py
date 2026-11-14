"""Print the markdown table of the 54 club words for docs/style-guide.md 12.2.   usage: python -I -X utf8 tools/re/cw_doctable.py"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FALLBACK = {3: 'Avalanc', 5: 'Monolit', 14: 'Topolin', 18: 'Cie', 19: 'Colmill', 20: 'Corrien', 24: 'Herenci', 31: 'Panther', 33: 'Ros'}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print('| # | `ja` (pool) | Logo | In the DB / default build | `--refit on` | Origin and meaning (art) |')
print('|--:|---|---|---|---|---|')
for row in csv.reader(open(os.path.join(ROOT, 'translation', 'clubwords_art.tsv'), encoding='utf8'), delimiter='\t'):
    if not row[0].isdigit():
        continue
    k = int(row[0])
    art, asc = row[2], row[3]
    base = FALLBACK.get(k, asc)
    refit = asc if k in FALLBACK else ''
    print('| %d | `%s` | %s | `%s` | %s | %s, "%s" |' % (k, row[1], art, base, ('`%s`' % refit) if refit else '', row[4], row[5]))
