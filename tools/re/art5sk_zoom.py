import os
from PIL import Image
R=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/build/art5/new/'
def g(k,box,s):
    im=Image.open(R+k+'.dec.png').convert('RGBA'); im=im.crop(box)
    bg=Image.new('RGBA',im.size,(40,110,60,255)); bg.alpha_composite(im)
    return bg.resize((im.width*s,im.height*s),Image.NEAREST)
parts=[g('03333',(0,0,350,140),2),g('07405',(0,0,110,200),2),g('02199',(0,0,128,32),3),
 g('03590',(130,0,256,256),3),g('02219',(0,0,128,100),3)]
W=sum(p.width for p in parts)+10*len(parts);H=max(p.height for p in parts)
c=Image.new('RGBA',(W,H),(0,0,0,255));x=0
for p in parts: c.paste(p,(x,0));x+=p.width+10
c.convert('RGB').save(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/build/art5sk/zoom.png');print(c.size)
for k in ('03823','03822'):
    pass
