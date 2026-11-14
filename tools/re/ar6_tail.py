import json,sys
f=sys.argv[1]; n=int(sys.argv[2]); m=int(sys.argv[3]) if len(sys.argv)>3 else 700
lines=open(f,encoding='utf8').read().splitlines()
for l in lines[-n:]:
    try: d=json.loads(l)
    except Exception: continue
    msg=d.get('message',{})
    c=msg.get('content')
    if isinstance(c,str): print('[%s] %s'%(msg.get('role'),c[:m])); continue
    for b in c or []:
        t=b.get('type')
        if t=='text': print('[text]',b['text'][:m])
        elif t=='tool_use': print('[use]',json.dumps(b['input'],ensure_ascii=False)[:m])
        elif t=='tool_result':
            cc=b.get('content')
            if isinstance(cc,list): cc=' '.join(x.get('text','') for x in cc if isinstance(x,dict))
            print('[res]',str(cc)[:m])
