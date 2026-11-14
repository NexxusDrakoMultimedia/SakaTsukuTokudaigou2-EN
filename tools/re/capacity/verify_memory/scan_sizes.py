# Size-literal / past-end-literal scan over all overlays + 1ST_READ + other root files.
import os,struct,csv,sys,glob
R='extracted'
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
def i(s): return int(s,0) if s else None
ov=[r for r in rows if r['base'] and r['dir']=='FLOW_PRG']
files={}
for p in glob.glob(R+'/**/*',recursive=True):
    if os.path.isfile(p): files[p.replace(chr(92),'/')]=open(p,'rb').read()
print('files',len(files))
# words index for target files: all 2-aligned offsets? SH literals 4 aligned within image; use both align 2 and 4 count
def words(b,al=2):
    return [(o,struct.unpack_from('<I',b,o)[0]) for o in range(0,len(b)-3,al)]
# 1) For each overlay: collect size-ish values
tot=0
print('== A. words equal to own file size / sectors / file_end / end_value in ANY file (4-aligned)')
import collections
targets={}
for r in ov:
    fs=int(r['file_size']); name=r['overlay']
    vals={'size':fs,'size+7ff':fs+0x7ff,'sectors':(fs+0x7ff)>>11,'sect*2048':((fs+0x7ff)>>11)<<11,'file_end':i(r['file_end']),'end_value':i(r['end_value'])}
    for k,v in vals.items():
        if v and v>0x1000: targets.setdefault(v,[]).append((name,k))
hits=collections.defaultdict(list)
for p,b in files.items():
    if len(b)<4: continue
    n=len(b)//4*4
    ws=struct.unpack_from('<%dI'%(n//4),b,0)
    for idx,w in enumerate(ws):
        if w in targets:
            hits[p].append((idx*4,w))
for p,h in sorted(hits.items()):
    for off,w in h:
        for nm,k in targets[w]:
            own = p.endswith('/'+nm)
            print(p,hex(off),hex(w),nm,k,'SELF' if own else 'other')
