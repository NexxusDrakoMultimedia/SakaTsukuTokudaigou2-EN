import json,random
S=[json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf8')]
P=[s for s in S if s['cat'].startswith(('prose','help')) and not s['skip']]
random.Random(11).shuffle(P)
for s in sorted(P[:60],key=lambda s:s['idx']):
    print('%d|%s|%d|%d|%s'%(s['idx'],s['cat'],s['max_bytes'],len(s['en'])+1,s['en_flat']))
