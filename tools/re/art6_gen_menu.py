import json
style = {'font': ['arial-bold-italic'], 'shear': 0.05, 'gradient': [[0, '#f4ffff'], [0.55, '#c8f8fa'], [1, '#86dcea']],
         'outline': {'color': '#06143a', 'width': 1.0}, 'shadow': {'color': '#000010', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
def mk(tid, labels, tmpl_y):
    regs = []
    for r, (ja, en) in labels.items():
        regs.append({'id': 'r%d' % r, 'ja': ja, 'text': en, 'x': 6, 'y': 32 * r + 4, 'w': 168, 'h': 26,
                     'erase': {'mode': 'copy', 'src': [0, tmpl_y]}, 'erase_rect': [0, 32 * r, 256, 32]})
    d = {'texture': tid, 'supersample': 4, 'quantize': 'argb4444', 'regions': regs,
         'defaults': {'style': 'm', 'align': 'right', 'size': 'auto', 'max_size': 21, 'min_sx': 0.72}, 'styles': {'m': style}}
    json.dump(d, open('tools/re/art6/%s.json' % tid, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
mk('37292', {0: ('練習指示', 'Practice Orders'), 1: ('基本方針変更', 'Change Policy'), 2: ('練習実行', 'Run Practice'), 3: ('特別調整', 'Special Prep'),
             4: ('連携を見る', 'View Teamwork'), 5: ('監督チーム診断', 'Manager Team Check'), 7: ('臨時休養', 'Extra Rest')}, 192)
mk('37293', {0: ('選手配置', 'Positions'), 1: ('システム', 'Formation'), 2: ('戦術', 'Tactics'), 3: ('中盤守備', 'Midfield Defence'),
             4: ('DFタイプ', 'DF Type'), 5: ('キッカー指定', 'Set Takers')}, 224)
