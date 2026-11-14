import os,sys,random
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
from common import *
rows=[r for r in load() if r['file'].startswith(('FLOW_PRG','ATFIRST'))]
random.seed(1)
def show(lbl,sel,k=12):
    s=[r for r in rows if sel(r)]
    print('==',lbl,len(s))
    for r in random.sample(s,min(k,len(s))): print('  ',r['file'][10:],r['max_bytes'],repr(r['ja'][:90]))
show('ref short<=5',lambda r:not r.get('orphan') and nchars(r['ja'])<5,25)
show('ref 5-10',lambda r:not r.get('orphan') and 5<=nchars(r['ja'])<10)
show('orph short',lambda r:r.get('orphan') and nchars(r['ja'])<10,15)
show('orph 40-60',lambda r:r.get('orphan') and 40<=nchars(r['ja']),10)
show('ref 15-30',lambda r:not r.get('orphan') and 15<=nchars(r['ja'])<30,15)
