import sys, glob, numpy as np
from PIL import Image
i,x0,y0,x1,y1,S,out=sys.argv[1],*map(int,sys.argv[2:7]),sys.argv[7]
a=Image.open(glob.glob('build/tex/ETC_DATA__TV_EVENT.ZAR/%s_*.png'%i)[0]).convert('RGBA').crop((x0,y0,x1,y1))
b=Image.open('build/art_tv/%s.dec.png'%i).convert('RGBA').crop((x0,y0,x1,y1))
m=Image.new('RGBA',(a.width*2+4,a.height),(255,0,255,255))
for k,im in enumerate((a,b)):
    bg=Image.new('RGBA',im.size,(40,40,60,255)); bg.alpha_composite(im); m.paste(bg,(k*(a.width+4),0))
m.resize((m.width*S,m.height*S),Image.NEAREST).save(out)
