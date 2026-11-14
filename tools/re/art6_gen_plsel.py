import json
big = {'font': ['impact', 'arial-black'], 'shear': 0.1, 'gradient': [[0, '#ffd060'], [0.5, '#ff9a20'], [0.52, '#ff7410'], [1, '#e85800']],
       'outline': {'color': '#401400', 'width': 1.0}, 'shadow': {'color': '#200800', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
small = {'font': ['arial-bold-italic'], 'gradient': [[0, '#ffe8c8'], [1, '#eca468']], 'outline': {'color': '#5a2a10', 'width': 0.7},
         'shadow': {'color': '#1c0c00', 'dx': 1, 'dy': 1, 'alpha': 1.0}}
clr = {'mode': 'clear'}
regs = [
 {'id': 'rate1', 'ja': 'チーム総合力', 'text': 'Team', 'x': 0, 'y': 0, 'w': 128, 'h': 24, 'style': 'big', 'align': 'left', 'size': 22, 'erase': clr},
 {'id': 'rate2', 'ja': 'チーム総合力', 'text': 'Rating', 'x': 0, 'y': 24, 'w': 128, 'h': 24, 'style': 'big', 'align': 'left', 'size': 22, 'erase': clr},
]
for i, (ja, en) in enumerate([('オフェンス', 'Offence'), ('タクティクス', 'Tactics'), ('ディフェンス', 'Defence'), ('システム', 'Formation'), ('スタミナ', 'Stamina')]):
    regs.append({'id': 's%d' % i, 'ja': ja, 'text': en, 'x': 0, 'y': 48 + 16 * i, 'w': 108, 'h': 16, 'style': 'small', 'align': 'left', 'size': 13, 'erase': clr})
d = {'texture': '37277', 'supersample': 4, 'quantize': 'argb4444', 'regions': regs, 'defaults': {'min_sx': 0.8}, 'styles': {'big': big, 'small': small}}
json.dump(d, open('tools/re/art6/37277.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
