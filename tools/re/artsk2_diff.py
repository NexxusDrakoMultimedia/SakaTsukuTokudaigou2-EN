import glob, numpy as np
from PIL import Image
for i in ('04080','04081','04082','04084','04085','04087','04089','04091','04093'):
    a=np.array(Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/%s_*.png'%i)[0]).convert('RGBA')).astype(int)
    b=np.array(Image.open('build/art_tv/%s.dec.png'%i).convert('RGBA')).astype(int)
    d=(np.abs(a-b).sum(2)>40)
    rows=np.where(d.any(1))[0]; 
    # row-run summary
    runs=[];s=None
    for y in range(len(d)):
        if d[y].any():
            if s is None: s=y
        elif s is not None: runs.append((s,y-1)); s=None
    if s is not None: runs.append((s,len(d)-1))
    print(i,[(r,int(d[r[0]:r[1]+1].any(0).nonzero()[0].min()),int(d[r[0]:r[1]+1].any(0).nonzero()[0].max())) for r in runs])
