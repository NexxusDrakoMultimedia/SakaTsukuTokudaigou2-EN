import sys,time,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import *
import sim
name=sys.argv[1]; r=float(sys.argv[2]); sp=float(sys.argv[3])
img=T.load_image('FLOW_PRG/%s.BIN'%name); ex=T.extract_image(img)
enc=sim.enc_for(ex[0],r,sp)
recs=[{'id':'%s#%x'%(img.source,s.off),'ja':T.decode_text(s.raw),'en':enc[s.off].decode()} for s in ex[0]]
t=time.time(); new,rep=T.insert_image(img,recs,extracted=ex); print(rep.line(),time.time()-t)
