import json
d=json.load(open('build/art/groups_v3.json',encoding='utf8'))
for p in d['packages']:
    if p.get('key')=='F' or p.get('id')=='F' or p.get('package')=='F' or str(p.get('name','')).startswith('F'):
        print(json.dumps(p,ensure_ascii=False,indent=1))
print([ (list(p)[:6]) for p in d['packages']][:1])
