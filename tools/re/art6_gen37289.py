import json
# column geometry
cols = {1: (2, 108), 2: (114, 108), 3: (226, 108)}
rows1 = ['Post Play', 'Attack Left', 'Attack Right', 'Central Break', 'Counter', 'Zonal Press', 'Offside Trap', 'Normal',
         'Zonal Press', 'Shooting', 'Dribbling', 'Pass Cut', 'GK Rush Out', None]
ja1 = ['ポストプレイ', '左サイドアタック', '右サイドアタック', '中央突破', 'カウンター', 'ゾーンプレス', 'オフサイドトラップ', 'ノーマル',
       'ゾーンプレス', 'シュート', 'ドリブル', 'パスカット', 'GK飛び出し', 'PK']
col2 = {4: ('Target Man', 'ポストプレイヤー'), 5: ('Dribbler', 'ドリブラー'), 6: ('Holding Mid', 'ボランチ'), 7: ('Stopper', 'ストッパー'),
        8: ('Goalkeeper', 'ゴールキーパー'), 9: ('Heading', 'ヘディング'), 10: ('Passing', 'パス'), 11: ('Tackling', 'タックル'),
        12: ('GK Saving', 'GKセービング'), 13: ('Place Kick', 'プレイスキック')}
col3 = {4: ('Striker', 'ストライカー'), 5: ('Playmaker', 'ゲームメーカー'), 6: ('Full-back', 'サイドバック'), 7: ('Libero', 'リベロ'),
        8: ('Endurance', '持久力強化'), 9: ('Speed', '瞬発力強化'), 10: ('Strength', '筋力強化'), 11: ('Line', 'ライン'),
        12: ('Libero', 'リベロ'), 13: ('Sweeper', 'スイーパー'), 14: ('Normal', 'ノーマル')}
regs = []
def add(id, ja, en, x, y, w, h, ex=0):
    regs.append({'id': id, 'ja': ja, 'text': en, 'x': x, 'y': y, 'w': w, 'h': h})
for r, en in enumerate(rows1):
    if en: add('c1r%d' % r, ja1[r], en, 4, 32 * r + 4, 104, 26)
for r, (en, ja) in col2.items(): add('c2r%d' % r, ja, en, 118, 32 * r + 4, 100, 26)
for r, (en, ja) in col3.items(): add('c3r%d' % r, ja, en, 230, 32 * r + 4, 100, 26)
json.dump({'texture': '37289', 'supersample': 4, 'quantize': 'argb4444', 'regions': regs,
 'defaults': {'style': 'trn', 'align': 'left', 'min_sx': 0.6, 'max_size': 20, 'erase': {'mode': 'hgrad'}, 'erase_grow': [0, 0, 1, 0]},
 'styles': {'trn': {'font': ['arial-bold-italic'], 'gradient': [[0, '#ffffff'], [0.5, '#dfe6fa'], [1, '#7c98ec']],
    'outline': {'color': '#0c1440', 'width': 1.2}, 'shadow': {'color': '#000010', 'dx': 1.5, 'dy': 1.5, 'alpha': 0.9}}}},
 open('tools/re/art6/37289.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
# plate-less column
d = json.load(open('tools/re/art6/37289.json', encoding='utf8'))
d['regions'] = [r for r in d['regions'] if r['id'] != 'c3r14']
clr = {'mode': 'clear'}
plain = [('c3r14', 'ノーマル', 'Normal', 230, 448)]
col4 = [(8, 'ポストプレイ', 'Post Play'), (9, '左サイドアタック', 'Attack Left'), (10, '右サイドアタック', 'Attack Right'), (11, '中央突破', 'Central Break'),
        (12, 'カウンター', 'Counter'), (13, 'ライン', 'Line'), (14, 'リベロ', 'Libero'), (15, 'スイーパー', 'Sweeper')]
for r, ja, en in col4:
    plain.append(('c4r%d' % r, ja, en, 342, 32 * r + 4))
for id, ja, en, x, y in plain:
    d['regions'].append({'id': id, 'ja': ja, 'text': en, 'x': x, 'y': y, 'w': 100, 'h': 26, 'erase': clr})
d['defaults']['size'] = 16
d['defaults']['max_size'] = 16
json.dump(d, open('tools/re/art6/37289.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
