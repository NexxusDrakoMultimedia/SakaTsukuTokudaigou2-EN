from PIL import Image
import numpy as np, glob,sys
f,x0,y0,x1,y1=sys.argv[1],*map(int,sys.argv[2:6])
a=np.array(Image.open(f).convert('RGBA')).astype(int)[y0:y1,x0:x1]
for r in range(a.shape[0]):
    row=a[r]; m=row[...,3]>=238
    if m.sum()<3: print(y0+r,'-'); continue
    l=row[m][:,:3].sum(1)
    px=row[m][l>=np.percentile(l,70)]
    print(y0+r,m.sum(),np.median(px,axis=0).astype(int),'dark',np.median(row[m][l<=np.percentile(l,15)],axis=0).astype(int))
