import json,re,collections
CTRL=re.compile(r'@[A-Z]/|@')
rows=[json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf-8')]
rows=[r for r in rows if not r['skip'] and r['cat'].startswith(('prose','help'))]
def w(s):
    s=CTRL.sub('',s); n=0
    for ch in s:
        n+= 1 if ('｡'<=ch<='ﾟ' or ord(ch)<128) else 2
    return n
jmax=collections.Counter(); more=0; tot=0; lcj=lce=0
for r in rows:
    jl=r['ja'].split('\n'); el=r['en'].split('\n')
    jmax[max(w(l) for l in jl)]+=1
    tot+=1; lcj+=len(jl); lce+=len(el); more+= len(el)>len(jl)
print('prose/help n',tot,'JP max-line half-width cols histogram (top):',sorted(jmax.items())[-8:])
print('mean lines JP %.2f EN %.2f ; EN has more lines than JP: %d (%.1f%%)'%(lcj/tot,lce/tot,more,100*more/tot))
print('EN max line chars:',max(max(len(CTRL.sub("",l)) for l in r['en'].split('\n')) for r in rows))
print('EN lines>4 :',sum(len(r['en'].split('\n'))>4 for r in rows),' JP lines>4:',sum(len(r['ja'].split('\n'))>4 for r in rows))
