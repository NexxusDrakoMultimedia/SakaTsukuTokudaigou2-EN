"""Magnify one decoded texture region on a flat background. usage: cw_tex8.py ID OUT.png SCALE [x0 y0 x1 y1]"""
import sys, glob
from PIL import Image
tid, out, sc = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
im = Image.open(glob.glob(f'build/tex/*/{tid:05d}_*.png')[0]).convert('RGBA')
if len(sys.argv) > 4: im = im.crop(tuple(map(int, sys.argv[4:8])))
bg = Image.new('RGBA', im.size, (120, 120, 128, 255)); bg.alpha_composite(im)
bg = bg.resize((bg.width*sc, bg.height*sc), Image.NEAREST).convert('RGB'); bg.save(out); print(out, bg.size)
