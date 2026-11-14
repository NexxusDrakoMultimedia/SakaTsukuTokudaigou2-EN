"""tx5 skeptic: scan every file of a built trial disc (except BCAST.BIN) for cp932 Japanese runs (>=4 double-byte chars, >=50% kana)
and report those that are not a ja string of the translation DB.   MSYS_NO_PATHCONV=1 python -I -X utf8 tools/re/tx5s_leftover.py NAME"""
import os, sys, re, json, glob, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import discbuild
name=sys.argv[1]
d=os.path.join(ROOT,'build','trial',name)
s=discbuild.Source(d if os.path.isdir(d) else os.path.join(ROOT,'build','trial'),name)
pvd,rl,rs,rec=discbuild.read_filesystem(s)
dbja=set()
for f in glob.glob(os.path.join(ROOT,'translation','*.jsonl')):
    for l in open(f,encoding='utf8'):
        r=json.loads(l); dbja.add(r['ja'])
big=chr(10).join(dbja)
rx=re.compile(rb'(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){4,}')
out=collections.defaultdict(list)
for r in rec:
    if r.isdir or r.path.upper()=='/BCAST/BCAST.BIN' or r.size>20_000_000: continue
    ext=r.path.rsplit('.',1)[-1].upper()
    data=s.read(r.lba,r.size)
    for m in rx.finditer(data):
        b=m.group()
        try: t=b.decode('cp932')
        except UnicodeDecodeError: continue
        kana=sum(1 for c in t if '぀'<=c<='ヿ')
        if kana*2<len(t) or kana<3: continue
        if t in dbja or t in big: continue
        out[r.path].append((m.start(),t))
tot=0
for p,v in sorted(out.items(),key=lambda x:-len(x[1])):
    print(len(v),p,[ (hex(o),t[:20]) for o,t in v[:4]])
    tot+=len(v)
print('total',tot,'files',len(out))
