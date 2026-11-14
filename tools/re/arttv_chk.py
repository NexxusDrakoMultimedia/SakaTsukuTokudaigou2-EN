from PIL import Image
import numpy as np
for t in ['04082','04085','04087','04089','04091','04093']:
    a=np.array(Image.open('build/art_tv/%s.dec.png'%t).convert('RGBA')).astype(int)
    y=(a[...,0]>230)&(a[...,1]>230)&(a[...,2]<90)&(a[...,3]>200)
    rows=np.where(y.sum(1)>0)[0]
    bands=[];s=rows[0];p=rows[0]
    for r in rows[1:]:
        if r!=p+1: bands.append((int(s),int(p))); s=r
        p=r
    bands.append((int(s),int(p)))
    print(t,bands)
