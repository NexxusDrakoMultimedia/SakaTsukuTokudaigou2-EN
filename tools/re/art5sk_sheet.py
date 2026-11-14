import json, os, sys, hashlib
from PIL import Image, ImageDraw
R=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/'
m=json.load(open(R+'build/art5/manifest.json'))
# dup coverage
miss=[];diff=[]
for k,v in m.items():
    hs=set()
    for f,t in v['copies']:
        p=R+'translation/textures/'+f+'/'+t+'.pvr'
        if not os.path.exists(p): miss.append((k,f,t)); continue
        hs.add(hashlib.md5(open(p,'rb').read()).hexdigest())
    if len(hs)>1: diff.append(k)
print('manifest',len(m),'missing',miss,'differing copies',diff)
ids=sorted(k for k in m if os.path.exists(R+'build/art5/new/%s.dec.png'%k))
out=R+'build/art5sk/'
def card(k):
    a=Image.open(R+'build/art5/orig/%s.png'%k).convert('RGBA')
    b=Image.open(R+'build/art5/new/%s.dec.png'%k).convert('RGBA')
    w,h=a.size
    c=Image.new('RGBA',(w*2+30,h+16),(70,70,90,255))
    for i,im in enumerate((a,b)):
        bg=Image.new('RGBA',im.size,(40,110,60,255)); bg.alpha_composite(im)
        c.paste(bg,(i*(w+30),16))
    ImageDraw.Draw(c).text((2,2),k+' '+str(m[k]['copies'][0]),fill=(255,255,255,255))
    return c
cards=[card(k) for k in ids]
# pack shelves width 1700
sheets=[];cur=[];x=y=rowh=0;W=1700;H=1500
def flush():
    pass
sh=Image.new('RGBA',(W,H),(0,0,0,255));x=y=rowh=0;n=0;names=[];cn=[]
for k,c in zip(ids,cards):
    if x+c.width>W: x=0;y+=rowh;rowh=0
    if y+c.height>H:
        sh.save(out+'sheet%d.png'%n);print('sheet',n,cn);n+=1;sh=Image.new('RGBA',(W,H),(0,0,0,255));x=y=rowh=0;cn=[]
    sh.paste(c,(x,y));x+=c.width+6;rowh=max(rowh,c.height+6);cn.append(k)
sh.save(out+'sheet%d.png'%n);print('sheet',n,cn)
