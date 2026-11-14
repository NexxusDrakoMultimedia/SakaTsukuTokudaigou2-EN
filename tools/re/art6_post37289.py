import json
p = 'tools/re/art6/37289.json'
d = json.load(open(p, encoding='utf8'))
for r in d['regions']:
    y = r['y'] - 2
    if r['id'].startswith('c1'): r['erase_rect'] = [1, y, 109, 29]
    elif r['id'].startswith('c2'): r['erase_rect'] = [114, y, 107, 29]
    elif r['id'].startswith('c3') and r['id'] != 'c3r14': r['erase_rect'] = [226, y, 108, 29]
    elif r['id'].startswith('c4') or r['id'] == 'c3r14': r['erase_rect'] = [r['x'] - 4, y, 112, 30]
json.dump(d, open(p, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
d = json.load(open(p, encoding='utf8'))
for r in d['regions']:
    if r['id'].startswith('c4') or r['id'] == 'c3r14':
        r['outline'] = {'color': '#1a2350', 'width': 0.8}
json.dump(d, open(p, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
