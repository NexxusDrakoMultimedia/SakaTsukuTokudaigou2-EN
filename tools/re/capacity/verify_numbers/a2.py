import json,glob,os
N=B=M=0
for f in sorted(glob.glob('translation/*.jsonl')):
    nm=os.path.basename(f)
    if not (nm.startswith('FLOW_PRG') or nm.startswith('ATFIRST')): continue
    for line in open(f,encoding='utf-8'):
        r=json.loads(line); N+=1; B+=len(r['ja'].encode('cp932')); M+=r['max_bytes']
print(N,B,B+N,M)
