import sys
from PIL import Image
import numpy as np
f,x0,y0,x1,y1,s,out=sys.argv[1],*map(int,sys.argv[2:7]),sys.argv[7]
im=Image.open(f).convert('RGBA').crop((x0,y0,x1,y1))
a=np.array(im)
print('alpha vals',np.unique(a[...,3])[:20], 'n',len(np.unique(a[...,3])))
# top colors of opaque pixels
from collections import Counter
c=Counter(map(tuple,a[a[...,3]>0].reshape(-1,4)))
print(c.most_common(10))
b=Image.new('RGBA',im.size,(110,110,110,255)); b.alpha_composite(im)
b.convert('RGB').resize((im.width*s,im.height*s),Image.NEAREST).save(out)
