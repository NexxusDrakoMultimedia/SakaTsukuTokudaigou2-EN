"""Crop+upscale a region of a contact sheet for reading. usage: classify_crop.py sheet x0 y0 x1 y1 scale out"""
import sys
from PIL import Image
s, x0, y0, x1, y1, sc, out = sys.argv[1:8]
im = Image.open(s).convert("RGB").crop((int(x0), int(y0), int(x1), int(y1)))
sc = float(sc)
im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
im.save(out)
