"""tx5 skeptic: for candidate strings print the exact bytes layout: start junk, text, covered-record starts inside the NUL-bounded run.
   python -I -X utf8 tools/re/tx5s_span.py FILE OFFSET_HEX ..."""
import os,sys,json,glob
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
src=sys.argv[1]
d=open(os.path.join(ROOT,'extracted',src),'rb').read()
fn=os.path.join(ROOT,'translation',src.replace('/','__')+'.jsonl')
starts={}
for l in open(fn,encoding='utf8'):
    r=json.loads(l); starts[int(r['id'].split('#')[1],16)]=r
def show(b):
    out=[];i=0
    while i<len(b):
        c=b[i]
        if c<0x20: out.append('<%02x>'%c if c!=0x0a else '\n'); i+=1
        elif 0x81<=c<=0x9f or 0xe0<=c<=0xfc:
            try: out.append(b[i:i+2].decode('cp932'))
            except: out.append('<%02x%02x>'%(c,b[i+1] if i+1<len(b) else 0))
            i+=2
        else: out.append(chr(c) if c<0x80 else '<%02x>'%c); i+=1
    return ''.join(out)
for a in sys.argv[2:]:
    pos=int(a,16); e=d.find(b'\0',pos)
    cut=[o for o in sorted(starts) if pos<o<e]
    print('== %s %x..%x len %d; covered starts inside: %s; byte before: %02x' % (src,pos,e,e-pos,[hex(x) for x in cut],d[pos-1]))
    seg=[pos]+cut+[e]
    for x,y in zip(seg,seg[1:]): print('  %x..%x %d: %s'%(x,y,y-x,show(d[x:y])))
