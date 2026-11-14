import csv, collections
rows = list(csv.reader(open('build/tex/index.tsv', encoding='utf-8'), delimiter='\t'))
want = ['ETC_DATA/SHTEX.ZAR','ATFIRST/SHTEX0.ZAR','ETC_DATA/SS_TEX.ZAR','ATFIRST/TITLEM.DAT','ETC_DATA/TITLEM.DAT','ETC_DATA/SH_ICON.ZAR','ETC_DATA/SUPPORT.ZAR','ATFIRST/SECFTEX0.ZAR','ATFIRST/HELP.DAT','ETC_DATA/HELP.DAT','ETC_DATA/OPTION.DAT','ETC_DATA/PLATE.ZAR','ETC_DATA/VMCOM.ZAR']
d = collections.defaultdict(set)
for r in rows[1:]:
    if r[1] in want and r[12]: d[r[1]].add(r[12])
for k,v in d.items(): print(k, sorted(v))
