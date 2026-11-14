import json
d=json.load(open('build/art/groups_v3.json',encoding='utf8'))
print(json.dumps(d['refit'],ensure_ascii=False,indent=1))
