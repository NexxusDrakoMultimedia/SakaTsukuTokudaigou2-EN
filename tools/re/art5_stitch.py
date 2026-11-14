"""art5_stitch OUT.png LEFT.png RIGHT.png : horizontal join"""
import sys
from PIL import Image
l, r = Image.open(sys.argv[2]).convert('RGBA'), Image.open(sys.argv[3]).convert('RGBA')
o = Image.new('RGBA', (l.width + r.width, l.height))
o.paste(l, (0, 0)); o.paste(r, (l.width, 0))
o.save(sys.argv[1])
