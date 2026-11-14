import json,glob,sys,collections
want=sys.argv[1:]
seen=collections.defaultdict(set)
for f in glob.glob('translation/*.jsonl'):
    if 'BCAST' in f: continue
    for l in open(f,encoding='utf8'):
        r=json.loads(l)
        for w in want:
            if w in r['ja'] and r.get('en'): seen[w].add((r['ja'][:60].replace('\n','/'),r['en'][:70].replace('\n','/'),r['max_bytes']))
for w in want:
    print('##',w)
    for x in list(seen[w])[:6]: print('  ',x)
