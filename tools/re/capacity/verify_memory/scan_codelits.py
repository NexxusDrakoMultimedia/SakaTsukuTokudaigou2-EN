# literal-pool (mov.l @(disp,PC),Rn) targets: which words pointing past the image end are really loaded by code?
import struct,csv
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
i=lambda s:int(s,0) if s else None
tot_raw=tot_code=0
print('overlay has_bss | words in [file_end,slot_end): raw, loaded-by-mov.l (decoded)')
for r in rows:
    if r['dir']!='FLOW_PRG' or not r['base'] or not r['slot_end'] or r['has_bss']!='0': continue
    b=open('extracted/FLOW_PRG/'+r['overlay'],'rb').read()
    fe=i(r['file_end']); se=i(r['slot_end']); ev=i(r['end_value'])
    tg=set()
    for o in range(0,len(b)-1,2):
        h=struct.unpack_from('<H',b,o)[0]
        if h>>12==0xd: tg.add(((o+4)&~3)+(h&0xff)*4)
    raw=code=0; ex=[]
    for o in range(0,len(b)-3,4):
        w=struct.unpack_from('<I',b,o)[0]
        if fe<=w<se and w!=ev:
            raw+=1
            if o in tg: code+=1; ex.append((hex(o),hex(w)))
    tot_raw+=raw; tot_code+=code
    if raw: print('%-12s %s | %4d %4d %s'%(r['overlay'],r['has_bss'],raw,code,ex[:5]))
print('total raw',tot_raw,'decoded-as-code-literal',tot_code,'(random-data false-positive expectation ~12%% = %d)'%(tot_raw*0.125))
