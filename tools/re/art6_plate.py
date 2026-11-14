import json
from PIL import Image
im = Image.open('build/art6/o_37292.png').convert('RGBA')
im.crop((0, 192, 256, 224)).save('tools/re/art6/plate_menu.png')
p = 'tools/re/art6/37293.json'
d = json.load(open(p, encoding='utf8'))
for r in d['regions']:
    r['erase'] = {'mode': 'plate', 'path': 'plate_menu.png', 'replace': True}
json.dump(d, open(p, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
