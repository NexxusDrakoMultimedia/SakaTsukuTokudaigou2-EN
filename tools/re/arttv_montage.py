import sys, glob
from PIL import Image
d='build/tex/ETC_DATA__TV_EVENT.ZAR/'
ids=['04080','04081','04082','04084','04085','04087','04089','04091','04093']
bg=(90,90,90)
W=3*260;H=3*260
m=Image.new('RGB',(W,H),bg)
for i,t in enumerate(ids):
    f=glob.glob(d+t+'_*.png')[0]
    im=Image.open(f).convert('RGBA')
    b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im)
    m.paste(b.convert('RGB'),((i%3)*260,(i//3)*260))
m.save('build/art_tv/montage.png')
