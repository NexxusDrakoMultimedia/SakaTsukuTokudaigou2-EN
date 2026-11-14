import os,sys,json,re
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
src=open('tools/re/capacity/ratio/build_sample.py',encoding='utf8').read().replace('\nmain()\n','\n')
bs={}; exec(compile(src,'bs','exec'),bs); vw=bs['vwidth']
over=0; tot=0; mx=0
for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf8'):
    s=json.loads(l)
    if s['skip'] or not s['cat'].startswith(('prose','help')): continue
    for ln in s['en'].split(chr(10)):
        tot+=1; w=vw(ln); mx=max(mx,w)
        if w>39: over+=1; print('OVER',s['idx'],w,ln)
print('prose/help lines',tot,'over 39:',over,'max width',mx)
# ASCII / forbidden checks over every non-skipped en
bad=0
for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf8'):
    s=json.loads(l)
    if s['skip']: continue
    e=s['en']
    if re.search('[^ -~'+chr(10)+']',e.replace('<09>','')) or chr(92) in e or '~' in e or '#' in re.sub(r'#[a-z0-9]+#','',e): bad+=1; print('BAD',s['idx'],e)
print('bad',bad)
