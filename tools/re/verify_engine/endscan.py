import struct,csv,sys
rows=list(csv.DictReader(open('tools/re/textengine/survey_overlays.tsv'),delimiter='\t'))
for r in rows:
    if not r['class'].startswith('no-bss'): continue
    d=open('extracted/FLOW_PRG/'+r['overlay'],'rb').read()
    base=int(r['base'],16); sz=len(d); ev=int(r['end_var_off'],16); end=int(r['_end'],16)
    assert sz==int(r['size'])
    def find(v):
        p=struct.pack('<I',v); o=[];i=-1
        while True:
            i=d.find(p,i+1)
            if i<0:break
            o.append(i)
        return o
    stubfirst=struct.unpack_from('<I',d,ev)[0]
    print(r['overlay'],'size',sz,'end',hex(end),'var@',hex(ev),'val',hex(stubfirst),
      '| _end occurrences',[hex(x) for x in find(end)],'| &var occ',[hex(x) for x in find(base+ev)],
      '| base+size occ',[hex(x) for x in find(base+sz)] if base+sz!=end else '=end','| ends-aligned',[hex(x) for x in find(((end+31)&~31)) ])
