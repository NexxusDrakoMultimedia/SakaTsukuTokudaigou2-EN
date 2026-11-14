import os,sys,json
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
src=open('tools/re/capacity/ratio/build_sample.py',encoding='utf8').read().replace('\nmain()\n','\n')
bs={}; exec(compile(src,'bs','exec'),bs); vw=bs['vwidth']
n=p=0
for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf8'):
    s=json.loads(l)
    if s['skip'] or not s['cat'].startswith(('prose','help')): continue
    for ln in s['en'].split(chr(10)):
        if vw(ln)==39: n+=1; p+= ln[-1] in '.,!?'
print('lines at width 39:',n,'of which end in . , ! ?:',p)
d=json.load(open('tools/re/capacity/ratio/analyze_out.json'))
tot=sum(v['maxb']-v['jb'] for _,v,_ in d['ovr']); tab=[(n_,v) for n_,v,_ in d['ovr'] if v.get('pin_n',0)>1000]
ts=sum(v['maxb']-v['jb'] for _,v in tab)
print('total slack',tot,'in overlays with >1000 pinned records',ts,len(tab),'overlays', ts/tot)
print('slack in 5 big prose',sum(v['maxb']-v['jb'] for n_,v,_ in d['ovr'] if n_ in('MEETING.BIN','NEWS.BIN','TRAINING.BIN','HELP.BIN','ATFIRST/HELP.BIN','DRAFT.BIN')))
print('mean extra in table overlays', sum(e for n_,v,e in d['ovr'] if v.get('pin_n',0)>1000)/len(tab))
v=[x for x in d['ovr'] if x[1].get('pin_n',0)>1000]
print(min(x[1]['jb'] for x in v),max(x[1]['jb'] for x in v),min(x[1]['maxb'] for x in v),max(x[1]['maxb'] for x in v),min(x[2] for x in v),max(x[2] for x in v))
