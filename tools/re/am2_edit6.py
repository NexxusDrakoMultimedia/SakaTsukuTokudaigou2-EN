p = 'tools/re/art5_pairs.py'
s = open(p, encoding='utf8').read()
s = s.replace("text='Oku', x=118, y=150, w=46, h=32, max_size=21, erase=HG)",
              "text='Oku', x=118, y=150, w=46, h=32, max_size=21, erase=UINK, erase_rect=[120, 147, 44, 32])")
s = s.replace("text='Man', x=244, y=150, w=64, h=32, max_size=21, erase=HG)",
              "text='Man', x=254, y=150, w=54, h=32, max_size=21, erase=UINK, erase_rect=[250, 147, 52, 32])")
s = s.replace("HG = {'mode': 'hgrad'}\n",
              "HG = {'mode': 'hgrad'}\n# am2: unit sprites (oku / man): light glyph ink and its dark shadow only, the plate bevel (luma ~90) stays\nUINK = {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 80}], 'dilate': 2, 'fill': 'diffuse', 'relax': 160}\n", 1)
open(p, 'w', encoding='utf8').write(s)
