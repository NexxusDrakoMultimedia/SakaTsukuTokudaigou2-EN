"""Crop and magnify a region of a PNG. usage: cw_crop.py IN.png OUT.png x0 y0 x1 y1 SCALE"""
import sys
from PIL import Image
i, o, x0, y0, x1, y1, s = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
im = Image.open(i).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize((im.width*s, im.height*s), Image.LANCZOS)
im.save(o); print(o, im.size)
