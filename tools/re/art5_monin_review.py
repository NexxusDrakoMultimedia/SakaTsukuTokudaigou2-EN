"""art5_monin_review: before/after strip of texture 03333 units rows -> build/art5/review/03333_before_after.png"""
import os, sys
from PIL import Image
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
A = os.path.join(R, 'build', 'art5')
o = Image.open(os.path.join(A, 'orig', '03333.png')).convert('RGBA')
b = Image.open(os.path.join(A, 'new', '03333.before.dec.png')).convert('RGBA')
a = Image.open(os.path.join(A, 'new', '03333.dec.png')).convert('RGBA')
box = (170, 20, 360, 262)
w, h = box[2] - box[0], box[3] - box[1]
c = Image.new('RGBA', (w * 3 + 16, h), (110, 110, 130, 255))
for i, im in enumerate((o, b, a)):
    c.alpha_composite(im.crop(box), (i * (w + 8), 0))
c = c.resize((c.width * 3, c.height * 3), Image.NEAREST).convert('RGB')
d = os.path.join(R, 'build', 'art5', 'review')
os.makedirs(d, exist_ok=True)
c.save(os.path.join(d, '03333_before_after.png'))
print(os.path.join(d, '03333_before_after.png'), c.size)
