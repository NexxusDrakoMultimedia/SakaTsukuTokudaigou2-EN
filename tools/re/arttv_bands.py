from PIL import Image
import numpy as np, glob
ids=['04082','04085','04087','04089','04091','04093']
for t in ids:
    f=glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/'+t+'_*.png')[0]
    a=np.array(Image.open(f).convert('RGBA')).astype(int)
    y=(a[...,0]>230)&(a[...,1]>230)&(a[...,2]<90)&(a[...,3]>200)
    rows=np.where(y.sum(1)>0)[0]
    # split into bands
    bands=[];s=rows[0];p=rows[0]
    for r in rows[1:]:
        if r!=p+1: bands.append((s,p)); s=r
        p=r
    bands.append((s,p))
    out=[]
    for s,e in bands:
        cols=np.where(y[s:e+1].sum(0)>0)[0]
        out.append((s,e,cols.min(),cols.max()))
    # first row of fully transparent beyond logo
    op=(a[...,3]>0).sum(1)
    print(t,out, 'alpha rows>0 first empty:', [i for i in range(256) if op[i]==0][:3])
