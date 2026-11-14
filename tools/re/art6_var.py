import sys, json
# art6_var.py ID STYLENAME 'json-overrides'  -> merges into styles[STYLENAME] (removing keys set to null)
p = 'tools/re/art6/%s.json' % sys.argv[1]
d = json.load(open(p, encoding='utf8'))
ov = json.loads(sys.argv[3])
st = d['styles'][sys.argv[2]]
for k, v in ov.items():
    if v is None: st.pop(k, None)
    else: st[k] = v
json.dump(d, open(p, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
