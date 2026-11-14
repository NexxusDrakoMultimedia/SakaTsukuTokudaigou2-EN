import json
for n, pf in (('00088', [[90, 32, 38, 31, 88]]), ('03642', [[104, 117, 46, 34, 102]])):
    q = 'tools/re/art1_spec/%s.json' % n
    d = json.load(open(q, encoding='utf8'))
    d['prefill'] = pf
    for r in d['regions']:
        if r['id'] == 'oku':
            r['erase'] = None
    json.dump(d, open(q, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
