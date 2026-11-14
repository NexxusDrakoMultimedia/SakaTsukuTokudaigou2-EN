import glob, numpy as np
from PIL import Image
a=np.array(Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/04080_*.png')[0]).convert('RGBA'))[:,:,3]
b=np.array(Image.open('build/art_tv/04080.dec.png').convert('RGBA'))[:,:,3]
for name,(y0,y1) in (('promo',(150,192)),('demo',(195,230))):
    for t,x in (('orig',a),('new',b)):
        c=(x[y0:y1]>40).sum(0)
        print(name,t,''.join('#' if v else '.' for v in c[:256]))
