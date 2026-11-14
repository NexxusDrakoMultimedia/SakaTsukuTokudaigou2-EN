import json, glob, re, collections
ids={}
for l in open('tools/re/tx5_t1_debug.tsv',encoding='utf8'):
    a,b=l.rstrip('\n').split('\t',1); ids[a]=b
spec=re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[a-zA-Z]|\n|<[0-9A-Fa-f]{2}>')
seen=0; bad=0
for f in glob.glob('translation/*.jsonl'):
    for l in open(f,encoding='utf8'):
        r=json.loads(l)
        if r['id'] in ids:
            seen+=1
            ja,en=r['ja'],r['en']
            if en!=ids[r['id']]: print('DIFF from tsv',r['id'],repr(en),repr(ids[r['id']]))
            if collections.Counter(spec.findall(ja))!=collections.Counter(spec.findall(en)):
                bad+=1; print('SPEC',r['id'],repr(ja),repr(en),r.get('max_bytes'))
            mb=r.get('max_bytes')
            if mb and len(en.encode('cp932'))>mb: print('LEN',r['id'],len(en),mb)
print(seen,len(ids),bad)
