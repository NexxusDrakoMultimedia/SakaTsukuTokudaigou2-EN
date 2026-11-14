from PIL import Image
import numpy as np, glob
for t in ['04082','04085','04087','04089','04091','04093']:
    f=glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/'+t+'_*.png')[0]
    a=np.array(Image.open(f).convert('RGBA')).astype(int)
    print(t,[(r,int((a[r,:,3]>0).sum()),int((a[r,:,3]>=238).sum())) for r in range(116,126)], 'last', [(r,int((a[r,:,3]>0).sum())) for r in range(164,172)])
