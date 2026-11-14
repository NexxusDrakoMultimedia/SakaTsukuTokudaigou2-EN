import sys,json,glob,os,collections
sys.path.insert(0,'tools'); import textdb
N=B=0; per=collections.Counter(); perc=collections.Counter()
for f in sorted(glob.glob('translation/*.jsonl')):
    nm=os.path.basename(f)
    if not (nm.startswith('FLOW_PRG') or nm.startswith('ATFIRST')): continue
    k=nm[:-6]
    for line in open(f,encoding='utf-8'):
        r=json.loads(line); L=len(textdb.encode_text(r['ja']))+1
        B+=L; N+=1; per[k]+=L; perc[k]+=1
print(N,B)
for k,v in per.most_common(8): print(k,perc[k],v)
