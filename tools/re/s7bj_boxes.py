"""s7bj_boxes: extents of red kana ink / tile panels in the 00101 logo."""
import numpy as np
from PIL import Image
a=np.asarray(Image.open('build/tex/ATFIRST__TITLE.DAT/00101_TITLE.DAT_9.png').convert('RGBA')).astype(int)
r,g,b,al=a[...,0],a[...,1],a[...,2],a[...,3]
red=(r>150)&(g<90)&(b<90)&(al>0)
for name,(x0,x1,y0,y1) in {'SA':(80,190,25,125),'KA':(80,190,115,205),'TSU':(325,440,25,125),'KU':(325,440,115,205)}.items():
    m=red[y0:y1,x0:x1]; ys,xs=np.nonzero(m)
    print(name,xs.min()+x0,xs.max()+x0,ys.min()+y0,ys.max()+y0,m.sum())
# dark tile panels: luma<70 columns
l=(r+g+b)//3
for y in (60,150):
    row=l[y]; print(y,[x for x in range(1,511) if (row[x]<80)!=(row[x-1]<80)][:30])
for x in (130,380):
    col=l[:,x]; print('x',x,[y for y in range(1,255) if (col[y]<80)!=(col[y-1]<80)][:30])
print(al[0,0],al[128,5])
