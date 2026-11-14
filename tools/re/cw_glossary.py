"""Append the 54 club words (logo-art spellings) to translation/glossary.tsv (idempotent: skipped when the block is present).
usage: python -I -X utf8 tools/re/cw_glossary.py"""
import csv, os, io
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
G = 'translation/glossary.tsv'
txt = open(G, encoding='utf8', newline='').read()
MARK = 'club word (logo art'
if MARK in txt:
    print('already present'); raise SystemExit
out = io.StringIO()
n = 0
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if not row[0].isdigit():
        continue
    k, ja, art, asc, lang, meaning = int(row[0]), row[1], row[2], row[3], row[4], row[5]
    note = '%s %d: logo %s, %s for "%s"' % (MARK + ')', k, art, lang, meaning)
    if row[11] != 'yes':
        note += '; art spelling too long for the in-place slot (%s), slot-fit form in the DB, art form in translation/refit' % row[11]
    if row[0] in ('2', '15', '38'):
        note += '; language per art, see docs/style-guide.md 12.2'
    out.write('%s\t%s\t\t%s\n' % (ja, asc, note))
    n += 1
if not txt.endswith('\n'):
    txt += '\n'
open(G, 'w', encoding='utf8', newline='').write(txt + out.getvalue())
print('appended', n, 'rows')
