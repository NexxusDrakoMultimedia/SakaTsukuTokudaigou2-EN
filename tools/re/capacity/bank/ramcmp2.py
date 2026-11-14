B=0x8c000000
fr=open('extracted/1ST_READ.BIN','rb').read()
nz=len(fr.rstrip(b'\0'))
print('last nonzero file off',hex(nz),'addr',hex(0x8c010000+nz))
# zero runs >=0x1000 in file
import re
runs=[(m.start(),m.end()) for m in re.finditer(rb'\0{4096,}',fr)]
tot=0
for s,e in runs:
    print('zero run file %x-%x  addr %x-%x len %d'%(s,e,0x8c010000+s,0x8c010000+e,e-s)); tot+=e-s
print('total',tot)
