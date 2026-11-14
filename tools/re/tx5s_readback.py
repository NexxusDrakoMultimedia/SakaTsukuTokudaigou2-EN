"""tx5 skeptic: read FILE of a built trial disc and print the text of the gap records as the game will read it (head + tail joined).
   MSYS_NO_PATHCONV=1 python -I -X utf8 tools/re/tx5s_readback.py NAME /FLOW_PRG/NENREP.BIN"""
import os, sys, json
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import discbuild, textfmt_common as C
name,path=sys.argv[1],sys.argv[2]
d=os.path.join(ROOT,'build','trial',name)
s=discbuild.Source(d if os.path.isdir(d) else os.path.join(ROOT,'build','trial'),name)
pvd,rl,rs,rec=discbuild.read_filesystem(s)
r=[x for x in rec if not x.isdir and x.path.upper()==path.upper()][0]
data=s.read(r.lba,r.size)
src=path.lstrip('/')
for l in open(os.path.join(ROOT,'translation',src.replace('/','__')+'.jsonl'),encoding='utf8'):
    j=json.loads(l)
    if j.get('fmt')!='gap': continue
    o=int(j['id'].split('#')[1],16)
    e=data.find(b'\0',o)
    print(j['id'].split('#')[1],'cont' if j.get('cont') else '    ','|',C.decode_text(data[o:e]).replace('\n','/'))
