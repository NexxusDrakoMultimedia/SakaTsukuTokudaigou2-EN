"""s7bj_crop: s7bj_crop.py IN.png OUT.png x y w h scale  (crop over green, nearest upscale)"""
import sys
from PIL import Image
i,o=sys.argv[1],sys.argv[2]; x,y,w,h=map(int,sys.argv[3:7]); s=int(sys.argv[7])
im=Image.open(i).convert('RGBA'); bg=Image.new('RGBA',im.size,(90,160,90,255)); bg.alpha_composite(im)
bg.crop((x,y,x+w,y+h)).resize((w*s,h*s),Image.NEAREST).save(o)
