import json
for n in ('07332', '10469'):
    q = 'tools/re/art1_spec/%s.json' % n
    d = json.load(open(q, encoding='utf8'))
    d['prefill'] = [[60, 126, 55, 37, 58]]
    for r in d['regions']:
        if r['id'] == 'man':
            r.pop('hsmooth', None); r['erase'] = None; r.pop('erase_rect', None)
    json.dump(d, open(q, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
