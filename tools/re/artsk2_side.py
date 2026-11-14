import sys, glob, os
sys.path.insert(0,'tools')
import numpy as np, pvr
from PIL import Image
out=sys.argv[1]; ids=sys.argv[2:]
m={'04080':'TV_EB.TBD#0','04081':'TV_EB.TBD#1','04082':'TV_E1.TBD#0','04084':'TV_E1.TBD#2','04085':'TV_E2.TBD#0','04087':'TV_E3.TBD#0','04089':'TV_E4.TBD#0','04091':'TV_E5.TBD#0','04093':'TV_E6.TBD#0'}
ims=[]
for i in ids:
    a=Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/%s_*.png'%i)[0]).convert('RGBA')
    data=open('translation/textures/ETC_DATA/TV_EVENT.ZAR/%s.pvr'%m[i],'rb').read()
    b=Image.fromarray(np.array(pvr.decode(data))).convert('RGBA')
    d=Image.open('build/art_tv/%s.dec.png'%i).convert('RGBA')
    print(i, a.size,b.size,'same_as_dec',np.array_equal(np.array(b),np.array(d)))
    w,h=a.size
    row=Image.new('RGBA',(w*2+4,h),(60,60,60,255))
    for k,im in enumerate((a,b)):
        bg=Image.new('RGBA',im.size,(40,40,60,255)); bg.alpha_composite(im); row.paste(bg,(k*(w+4),0))
    ims.append(row)
W=max(r.width for r in ims); H=sum(r.height for r in ims)
mm=Image.new('RGBA',(W,H)); y=0
for r in ims: mm.paste(r,(0,y)); y+=r.height
mm.save(out)
