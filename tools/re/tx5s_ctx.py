"""tx5 skeptic: show the raw bytes (cp932 decoded, controls as <xx>) around OFFSET of extracted/FILE and the DB records near it.
   python -I -X utf8 tools/re/tx5s_ctx.py FLOW_PRG/RECON.BIN 0x21507 [before=96 after=160]"""
import sys, json, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
p=sys.argv[1]; o=int(sys.argv[2],16); bef=int(sys.argv[3]) if len(sys.argv)>3 else 96; aft=int(sys.argv[4]) if len(sys.argv)>4 else 160
d=open(os.path.join(ROOT,'extracted',p),'rb').read()
def show(b):
    out=[];i=0
    while i<len(b):
        c=b[i]
        if c<0x20 or c==0x7f: out.append('<%02x>'%c); i+=1
        elif (0x81<=c<=0x9f or 0xe0<=c<=0xfc) and i+1<len(b):
            try: out.append(b[i:i+2].decode('cp932'))
            except: out.append('<%02x%02x>'%(c,b[i+1]))
            i+=2
        else: out.append(chr(c) if c<0x80 else '<%02x>'%c); i+=1
    return ''.join(out)
print(show(d[o-bef:o]),'||',show(d[o:o+aft]))
fn=os.path.join(ROOT,'translation',p.replace('/','__')+'.jsonl')
for l in open(fn,encoding='utf8'):
    r=json.loads(l); a=int(r['id'].split('#')[1],16)
    if o-bef-120<=a<=o+aft: print(hex(a),r['max_bytes'],repr(r['ja'][:60]),'|',repr(r['en'][:50]),r['ctx'][:40])
