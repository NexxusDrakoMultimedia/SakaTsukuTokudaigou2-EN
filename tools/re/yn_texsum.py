import csv, collections
c = collections.Counter(); 
rows = list(csv.reader(open('build/tex/index.tsv', encoding='utf-8'), delimiter='\t'))
h = rows[0]
for r in rows[1:]:
    c[r[1]] += 1
for k, v in sorted(c.items()): print(k, v)
