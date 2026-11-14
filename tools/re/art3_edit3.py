import json
p = 'translation/art/03584.json'
s = json.load(open(p, encoding='utf8'))
for r in s['regions']:
    if r['id'] == 'scout_notes':
        r['x'], r['w'], r['y'], r['h'] = 217, 140, 175, 25
        r['erase'] = {'mode': 'copy', 'src': [217, 212]}
        r.pop('erase_rect', None)
json.dump(s, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
