"""tx5 skeptic: broader candidate pass (kanji-only too): NUL-bounded strings, no bad bytes, >=2 full-width chars, no control bytes other than \n,
NOT covered by a translation record.  Prints those not already in build/skep/gaps.tsv.   python -I -X utf8 tools/re/tx5s_gap3.py"""
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
seen=set()
for l in open(os.path.join(ROOT,'build','skep','gaps.tsv'),encoding='utf8'):
    p=l.split('\t'); 
    if len(p)>=2: seen.add((p[0],p[1]))
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
        if len(s)>=4 and (pos==0 or d[pos-1]==0):
            c=textdb.classify_text(s)
            if c['bad']==0 and c['full']>=2 and c['ctrl']==0 and c['inc_run']<5 and c['level2']*3<=c['full'] and c['hw']<=2 and c['full']*2>=len(s)*0.6:
                i=bisect.bisect_right(st,pos)-1
                ok=any(iv[j][0]<=pos<iv[j][1] for j in range(max(0,i-6),i+1)) if iv else False
                if not ok and (src,'%x'%pos) not in seen:
                    print('%s\t%x\t%d\t%s'%(src,pos,len(s),show(s))); n+=1
        pos=e+1
print('n',n)
