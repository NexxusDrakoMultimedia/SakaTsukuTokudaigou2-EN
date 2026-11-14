# For every FLOW_PRG overlay: literal words (4-aligned and 2-aligned) pointing into [file_end, end_rounded+0x4000) other than ENDVAR itself,
# and words in [end_rounded, slot_end) (heap region addresses baked into code).
import struct,csv,collections
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
def i(s): return int(s,0) if s else None
out=[]
for r in rows:
    if r['dir']!='FLOW_PRG' or not r['base']: continue
    nm=r['overlay']; b=open('extracted/FLOW_PRG/'+nm,'rb').read()
    base=i(r['base']); fe=i(r['file_end']); ev=i(r['end_value']); er=i(r['end_rounded']); se=i(r['slot_end'])
    bss=int(r['bss_bytes'] or 0)
    # exact-aligned words
    near=[];heapw=[]
    for off in range(0,len(b)-3,4):
        w=struct.unpack_from('<I',b,off)[0]
        if fe<=w<ev+0x40 and w!=ev:   # inside file_end.._end window (BSS or padding)
            near.append((off,w))
        if se and er<=w<se and w!=ev: heapw.append((off,w))
    out.append((nm,r['has_bss'],bss,len(near),len(heapw),near[:3],heapw[:3]))
    
print('overlay has_bss bss_bytes n_words_in[file_end,_end+0x40) n_words_in_heap')
for o in out:
    if o[1]=='0' : print(o[0],o[2],o[3],o[4],[(hex(a),hex(w)) for a,w in o[5]],[(hex(a),hex(w)) for a,w in o[6]])
print('--- bss overlays totals', sum(1 for o in out if o[1]=='1'), 'with words past end:',sum(1 for o in out if o[1]=='1' and o[4]))
print('--- no-bss overlays', sum(1 for o in out if o[1]=='0'), 'with words in window:',sum(1 for o in out if o[1]=='0' and o[3]),'with heap words:',sum(1 for o in out if o[1]=='0' and o[4]))
