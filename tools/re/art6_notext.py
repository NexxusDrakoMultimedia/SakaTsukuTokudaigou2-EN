import json, sys
d = json.load(open('tools/re/art6/%s.json' % sys.argv[1], encoding='utf8'))
for r in d['regions']: r.pop('text', None)
json.dump(d, open('tools/re/art6/%s.json' % sys.argv[2], 'w', encoding='utf8'), indent=1, ensure_ascii=False)
