"""tx5 skeptic: NUL-delimited cp932 strings of every overlay image that no translation record covers (record offset .. +max_bytes).
Candidates: bad == 0, >= 3 full-width chars with >= 2 kana (or markup text), not mostly noise.  Writes build/skep/gaps.tsv  (file, offset, text with <xx> controls).
   python -I -X utf8 tools/re/tx5s_gap2.py"""
import os, sys, json, glob, bisect, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import textdb
cov=collections.defaultdict(list)
for f in glob.glob(os.path.join(ROOT,'translation','*.jsonl')):
    if os.path.basename(f).startswith('BCAST'): continue
    for l in open(f,encoding='utf8'):
        r=json.loads(l); p,o=r['id'].rsplit('#',1)
        try: o=int(o,16)
        except ValueError: continue
        cov[p].append((o,o+(r.get('max_bytes') or len(r['ja'].encode('cp932','replace'))+1)))
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
os.makedirs(os.path.join(ROOT,'build','skep'),exist_ok=True)
out=open(os.path.join(ROOT,'build','skep','gaps.tsv'),'w',encoding='utf8')
n=0
for src,path in textdb.list_sources():
    if src=='1ST_READ.BIN': continue
    iv=sorted(cov.get(src,[])); st=[a for a,b in iv]
    d=open(path,'rb').read()
    pos=0
    while pos<len(d):
        e=d.find(b'\0',pos)
        if e<0: e=len(d)
        s=d[pos:e]
        if len(s)>=6:
            c=textdb.classify_text(s)
            if c['bad']==0 and c['full']>=3 and c['kana']>=2 and c['inc_run']<8:
                i=bisect.bisect_right(st,pos)-1
                ok=any(iv[j][0]<=pos<iv[j][1] for j in range(max(0,i-6),i+1)) if iv else False
                if not ok:
                    out.write('%s\t%x\t%d\t%s\n'%(src,pos,len(s),show(s).replace('\n','\n'))); n+=1
        pos=e+1
print('candidates',n)
