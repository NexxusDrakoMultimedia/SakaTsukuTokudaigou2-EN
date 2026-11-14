import json
p = 'translation/art/03583.json'
s = json.load(open(p, encoding='utf8'))
s['defaults']['size'] = 19
s['defaults'].pop('max_size', None)
json.dump(s, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
