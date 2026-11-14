"""mn5_slack.py [TSV]: list the %m records whose window allows fewer than 17 glyphs per %m (build/mn5/budget.tsv from mny_budget.py), with the compact form's saving."""
import csv, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'build/mn5/budget.tsv'
rows = list(csv.DictReader(open(p, encoding='utf8'), delimiter='\t'))
bad = [r for r in rows if int(r['slack(glyphs per %m)']) < 17]
for r in sorted(bad, key=lambda r: int(r['slack(glyphs per %m)'])):
    print('%-36s %-9s slack %2s  over@15 %s over@17 %s  %s' % (r['id'], r['window'], r['slack(glyphs per %m)'], r['over cells @TYPICAL 15'], r['over cells @CAP 17'], r['en'][:50].replace('|', '/')))
print(len(bad), 'of', len(rows))
