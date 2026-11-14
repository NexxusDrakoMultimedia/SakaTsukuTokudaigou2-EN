import json
st = {'font': ['arial-black'], 'shear': 0.12, 'gradient': [[0, '#ffffff'], [0.55, '#e4eaff'], [1, '#8aa4f0']],
      'outline': {'color': '#0c1440', 'width': 0.8}, 'shadow': {'color': '#000010', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
regs = []
for i, ja in enumerate(['FWタイプ', 'MFタイプ']):
    regs.append({'id': 't%d' % i, 'ja': 'タイプ', 'text': 'Type', 'x': 50, 'y': 32 * i + 2, 'w': 76, 'h': 28, 'size': 18, 'align': 'left',
                 'erase': {'mode': 'hgrad'}, 'erase_rect': [49, 32 * i + 1, 80, 29]})
d = {'texture': '37281', 'supersample': 4, 'quantize': 'argb4444', 'regions': regs, 'defaults': {'style': 's'}, 'styles': {'s': st}}
json.dump(d, open('tools/re/art6/37281.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
