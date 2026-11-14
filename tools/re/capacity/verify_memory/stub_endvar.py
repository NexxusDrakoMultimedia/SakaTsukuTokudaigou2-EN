# Execute the real entry stub (tools/sh4stub.py via memmap.run_overlay_stub) of every L2-eligible overlay twice: original image and image with the `_end` word raised by +0x1000.
# If the stub honours _end, the heap start (hook kind: r6; direct kind: written end) moves by exactly +0x1000 and nothing else changes.
import sys,struct,csv
sys.path.insert(0,'tools')
import build_patch as bp, textdb, memmap
from sh4stub import StubError
surv=bp.load_survey()
rows=list(csv.DictReader(open('build/memmap/overlays.tsv'),delimiter='\t'))
ok=bad=0
for r in rows:
    if r['dir']!='FLOW_PRG' or not r['base']: continue
    src='FLOW_PRG/'+r['overlay']
    img=textdb.load_image(src)
    off=bp.append_eligible(src,img,surv)
    if off is None: continue
    d=bytes(img.data)
    a=memmap.run_overlay_stub(d,None) if False else None
    try:
        a=memmap.run_overlay_stub(d,[(0x8c2d0000+i*0x100000,0x100000) for i in range(8)])
        dd=bytearray(d); e=struct.unpack_from('<I',dd,off)[0]; struct.pack_into('<I',dd,off,e+0x1000)
        b=memmap.run_overlay_stub(bytes(dd),[(0x8c2d0000+i*0x100000,0x100000) for i in range(8)])
    except Exception as ex:
        print(r['overlay'],'ERR',repr(ex)); bad+=1; continue
    if not a or not b: print(r['overlay'],'stub not decoded',a is None,b is None); bad+=1; continue
    key='r6' if a['kind']=='hook' else 'end'
    delta=b[key]-a[key]
    same=all(a.get(k)==b.get(k) for k in ('target','r4','r5','kind') )
    fine=(delta==0x1000) and same
    ok+=fine; bad+= (not fine)
    print('%-12s kind %-6s %s %#x -> %#x delta %#x %s'%(r['overlay'],a['kind'],key,a[key],b[key],delta,'OK' if fine else '<<< DIFFERENT'))
print('honours _end (+0x1000 -> heap start +0x1000):',ok,' other:',bad)
