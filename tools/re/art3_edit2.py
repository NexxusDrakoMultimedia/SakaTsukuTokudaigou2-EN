import json
p = 'translation/art/03584.json'
s = json.load(open(p, encoding='utf8'))
s['art3_row_mode'] = [{'x': [127, 188], 'y': [288, 299]}, {'x': [191, 241], 'y': [288, 299]}, {'x': [247, 294], 'y': [288, 299]},
                      {'x': [296, 379], 'y': [288, 299]}, {'x': [384, 459], 'y': [288, 299]}]
for r in s['regions']:
    if r['id'] == 'scout_notes':
        r['erase'] = {'mode': 'copy', 'src': [212, 212]}
    if r['id'] in ('flair', 'technique', 'intel', 'physical', 'mental'):
        r['y'] = 270
        r['h'] = 24
        r['size'] = 17
        r['erase_rect'] = [r['x'], 270, r['w'], 18]
        r['valign'] = 'top'
        r['dy'] = 1
json.dump(s, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
