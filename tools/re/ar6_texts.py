import json,sys
f=sys.argv[1]
for i,l in enumerate(open(f,encoding='utf8').read().splitlines()):
    try: d=json.loads(l)
    except Exception: continue
    msg=d.get('message',{})
    if msg.get('role')!='assistant': continue
    c=msg.get('content')
    if isinstance(c,str): print(i,c[:600]); continue
    for b in c or []:
        if b.get('type')=='text' and len(b['text'])>20: print(i,b['text'][:700].replace('\n',' '))
