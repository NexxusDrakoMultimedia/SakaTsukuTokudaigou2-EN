p='tools/re/arttv_build.py'
s=open(p,encoding='utf8').read()
a=s.index("    reg.append({'id': 'promoted'")
b=s.index("    return {'size': [256, 256], 'quantize': 'argb4444', 'styles': STYLES, 'regions': reg}\n\n\ndef spec_head")
new='''    for rid, word, y, ey, eh in (('promoted', 'Promoted', 148, 146, 44), ('demoted', 'Demoted', 190, 190, 46)):
        # the Japanese had a gap at x138..148 between the two words; keep each word on its own side of it
        reg.append({'id': rid + '_a', 'text': 'TV Station', 'x': 4, 'y': y, 'w': 132, 'h': 40,
                    'erase_rect': [0, ey, 140, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.7,
                    'align': 'left', 'valign': 'middle', 'pad': 2})
        reg.append({'id': rid + '_b', 'text': word, 'x': 146, 'y': y, 'w': 108, 'h': 40,
                    'erase_rect': [140, ey, 116, eh], 'erase': CLEAR, 'style': rid, 'size': 27, 'min_sx': 0.7,
                    'align': 'left', 'valign': 'middle', 'pad': 2})
'''
open(p,'w',encoding='utf8').write(s[:a]+new+s[b:])
