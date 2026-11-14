import sys,json,glob,os,collections
sys.path.insert(0,'tools')
import textdb
rows=[]
for f in sorted(glob.glob('translation/*.jsonl')):
    n=os.path.basename(f)[:-6]
    for l in open(f,encoding='utf8'):
        r=json.loads(l); r['file']=n; rows.append(r)
print(len(rows))
print(collections.Counter(type(r['max_bytes']).__name__ for r in rows))
print(collections.Counter(r['file'].split('__')[0] for r in rows))
nm=[r for r in rows if r['max_bytes'] is None]
print(collections.Counter(r['file'] for r in nm).most_common(20))
print(nm[:3])
