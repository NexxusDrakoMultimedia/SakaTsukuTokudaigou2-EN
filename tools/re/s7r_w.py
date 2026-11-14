"""s7r_w FONT SIZE text... : pixel width of texts in an arttext font alias"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import arttext
from PIL import ImageFont
font, size = sys.argv[1], int(sys.argv[2])
p = arttext.resolve_font(font)[0]
print(p)
f = ImageFont.truetype(p, size)
for t in sys.argv[3:]:
    print(t, f.getlength(t))
