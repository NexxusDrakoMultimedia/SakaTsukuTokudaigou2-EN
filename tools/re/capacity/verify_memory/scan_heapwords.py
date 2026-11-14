import struct,csv,collections
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
def i(s): return int(s,0) if s else None
for r in rows:
    if r['dir']!='FLOW_PRG' or not r['base'] or r['has_bss']!='0' or not r['slot_end']: continue
    nm=r['overlay']; b=open('extracted/FLOW_PRG/'+nm,'rb').read()
    er=i(r['end_rounded']); se=i(r['slot_end']); ev=i(r['end_value'])
    ws=[(o,struct.unpack_from('<I',b,o)[0]) for o in range(0,len(b)-3,4)]
    h=[(o,w) for o,w in ws if er<=w<se and w!=ev]
    al=[(o,w) for o,w in h if w&0x1f==0]
    # unique values
    uv=sorted(set(w for o,w in h))
    print(nm,'heap-range words',len(h),'unique',len(uv),'32-aligned',len(al),[hex(w) for o,w in al[:6]])
