"""tx5 skeptic: Japanese (cp932, >=3 kana, >=4 chars) in extracted/ files that lies OUTSIDE every translation record's byte range
(offset .. offset+max_bytes).  These are strings the extractors missed (like NENREP 0x23487).
   python -I -X utf8 tools/re/tx5s_gaps.py [prefix ...]"""
import os, re, sys, json, glob, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
rx=re.compile(rb'(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){4,}')
only=sys.argv[1:]
cov=collections.defaultdict(list)
for f in glob.glob(os.path.join(ROOT,'translation','*.jsonl')):
    b=os.path.basename(f)
    if b.startswith('BCAST'): continue
    for l in open(f,encoding='utf8'):
        r=json.loads(l)
        p,o=r['id'].rsplit('#',1)
        try: o=int(o,16)
        except ValueError: continue
        cov[p].append((o,o+max(r.get('max_bytes') or 0,len(r['ja'].encode('cp932','replace')))+1))
tot=0; rows=[]
for p,iv in cov.items():
    if only and not any(p.startswith(x) for x in only): continue
    fp=os.path.join(ROOT,'extracted',p)
    if not os.path.exists(fp): continue
    d=open(fp,'rb').read()
    iv.sort()
    import bisect
    starts=[a for a,b in iv]
    miss=[]
    for m in rx.finditer(d):
        try: t=m.group().decode('cp932')
        except: continue
        k=sum(1 for c in t if '぀'<=c<='ヿ')
        if k<3 or k*2<len(t): continue
        o=m.start()
        i=bisect.bisect_right(starts,o)-1
        ok=False
        # any interval covering o (check a few predecessors for nested)
        for j in range(max(0,i-6),i+1):
            if iv[j][0]<=o<iv[j][1]: ok=True;break
        if not ok: miss.append((o,t))
    if miss: rows.append((len(miss),p,miss))
rows.sort(reverse=True)
for n,p,m in rows[:60]:
    print(n,p,[(hex(o),t[:16]) for o,t in m[:3]])
print('files',len(rows),'total',sum(r[0] for r in rows))
