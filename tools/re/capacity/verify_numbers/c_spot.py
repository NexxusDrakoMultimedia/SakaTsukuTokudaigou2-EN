import json,random
rows=[json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf-8')]
rows=[r for r in rows if not r['skip']]
random.Random(7).shuffle(rows)
for r in rows[:40]:
    print('#%d [%s] max=%d'%(r['idx'],r['cat'],r['max_bytes'])); print('JA:',r['ja'].replace('\n','|')); print('EN:',r['en_flat']); print()
