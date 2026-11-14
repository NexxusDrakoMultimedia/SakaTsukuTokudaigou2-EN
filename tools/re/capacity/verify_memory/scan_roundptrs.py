# Fixed private buffers: literal words in [end_rounded, slot_end) that are multiples of 0x400 (random-noise probability 1/1024 per heap-range word)
import struct,csv,collections
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
i=lambda s:int(s,0) if s else None
print('overlay has_bss base er slot_end | round (0x400-aligned) words inside [heap_start,slot_end): count, distinct, first')
for r in rows:
    if r['dir']!='FLOW_PRG' or not r['base'] or not r['slot_end']: continue
    b=open('extracted/FLOW_PRG/'+r['overlay'],'rb').read()
    er=i(r['end_rounded']); se=i(r['slot_end']); ev=i(r['end_value'])
    ws=[(o,struct.unpack_from('<I',b,o)[0]) for o in range(0,len(b)-3,4)]
    h=[(o,w) for o,w in ws if er<=w<se and w!=ev and w&0x3ff==0]
    if h:
        print('%-12s bss=%s %s %s %s | %d %d %s'%(r['overlay'],r['has_bss'],r['base'],r['end_rounded'],r['slot_end'],len(h),len(set(w for o,w in h)),[hex(w) for o,w in h[:6]]))
