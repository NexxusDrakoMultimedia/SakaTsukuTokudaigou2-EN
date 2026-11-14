import re,csv
rows={r['overlay']:r for r in csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t')}
ds=None; cur=None; slots={}
for l in open('build/memmap/heaps.txt'):
    if l.startswith('== '): ds=l.split()[1]; continue
    m=re.match(r'slot\s+(\d+) state (\d+) base (\w+) size (\w+) \| heap (\w+)\.\.(\w+) \((\w+)\)',l)
    if m: slots[(ds,int(m.group(1)))]={'heap':int(m.group(7),16),'start':int(m.group(5),16),'end':int(m.group(6),16),'used':[],'free':[]}; continue
    m=re.match(r'\s+slot\s+(\d+) blocks:',l)
    if m: cur=(ds,int(m.group(1))); continue
    m=re.match(r'\s+([0-9a-f]{8})\s+(\d+) (USED|free)',l)
    if m and cur: slots[cur]['used' if m.group(3)=='USED' else 'free'].append((int(m.group(2)),int(m.group(1),16)))
meas={('ram_2400',1):'MOVIE_BG',('ram_2400',5):'TITLE',('live1_ram',1):'S_SELECT',('live1_ram',7):'N_ENTRY',('live3_ram',1):'CLUBEDIT',('ram_2400',10):'HELP',('ram_2400',11):'FACEMDUL'}
print('dump slot overlay | heap | used_sum | largest USED | largest free | append_cons | heap-append_cons | verdict (used_sum<=heap-cons ; largest_used<=largest_free_after_cons?)')
for k,ov in meas.items():
    v=slots.get(k)
    if not v: continue
    r=rows.get(ov+'.BIN'); cons=int(r['append_cons'] or 0) if r else 0
    us=sum(a for a,b in v['used']); lu=max(v['used'])[0] if v['used'] else 0
    lf=max(v['free'])[0] if v['free'] else 0
    print(k,ov,v['heap'],us,lu,lf,cons,v['heap']-cons,'OK-sum' if us<=v['heap']-cons else 'SUM-EXCEEDS','OK-frag' if lf-cons>=0 else 'largest free block smaller than cons')

print()
print('== hard-coded heap addresses: literal words of the overlay image that equal (block+0x20) of a malloc block in the dump (any state)')
import struct
img={'CLUBEDIT':'CLUBEDIT.BIN','S_SELECT':'S_SELECT.BIN','N_ENTRY':'N_ENTRY.BIN','TITLE':'TITLE.BIN','HELP':'HELP.BIN','FACEMDUL':'FACEMDUL.BIN','MOVIE_BG':'MOVIE_BG.BIN'}
for k,ov in meas.items():
    v=slots[k]; blocks={b+0x20 for a,b in v['used']+v['free']}|{b for a,b in v['used']+v['free']}
    b=open('extracted/FLOW_PRG/'+img[ov],'rb').read()
    ws=[(o,struct.unpack_from('<I',b,o)[0]) for o in range(0,len(b)-3,4)]
    hit=[(hex(o),hex(w)) for o,w in ws if w in blocks and w>=v['start']]
    heapw=[w for o,w in ws if v['start']<=w<v['end']]
    print(k,ov,'blocks',len(blocks)//2,'literal words inside heap range',len(heapw),'== block address:',len(hit),hit[:6])
