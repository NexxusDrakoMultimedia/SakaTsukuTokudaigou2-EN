"""Real JP byte length (encode_text) per overlay and globally unique; English demand model ratios."""
import sys,json,glob,os
sys.path.insert(0,'tools')
import textdb
tot=0; totu=0; seen={}; per={}
nrec=0
for p in sorted(glob.glob('translation/FLOW_PRG__*.jsonl'))+sorted(glob.glob('translation/ATFIRST__*.jsonl')):
    b=0;slack=0;n=0
    for l in open(p,encoding='utf8'):
        r=json.loads(l); eb=len(textdb.encode_text(r['ja']))+1
        b+=eb; n+=1
        slack+=(r['max_bytes'] or eb)-eb
        if r['ja'] not in seen: seen[r['ja']]=eb
    per[os.path.basename(p)[:-6]]=(n,b,slack)
    tot+=b; nrec+=n
print('overlay records',nrec,'JP text bytes incl NUL',tot,'sum slack (max_bytes-len)',sum(v[2] for v in per.values()))
print('globally unique ja strings',len(seen),'bytes',sum(seen.values()))
import statistics
lens=[len(k) for k in seen]  # char counts
print('avg chars/string (unique)',statistics.mean(lens))
for k,v in sorted(per.items(),key=lambda x:-x[1][1])[:8]: print(k,v)
