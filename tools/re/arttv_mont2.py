from PIL import Image
import glob
ids=['04081','04083','04084','04086','04088','04090','04092','04094']
bg=(90,90,90)
m=Image.new('RGB',(4*260,2*260),bg)
for i,t in enumerate(ids):
    f=glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/'+t+'_*.png')[0]
    im=Image.open(f).convert('RGBA'); b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im)
    m.paste(b.convert('RGB'),((i%4)*260,(i//4)*260))
m.save('build/art_tv/montage2.png')
