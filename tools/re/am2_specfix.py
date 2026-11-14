"""am2_specfix - switch the header 'man' erase from hgrad to a row-interpolated plate (hsmooth) in group-1 specs."""
import json
for n in ('00002', '10475', '07332', '10469'):
    p = 'tools/re/art1_spec/%s.json' % n
    d = json.load(open(p, encoding='utf8'))
    for r in d['regions']:
        if r.get('id') == 'man' and r.get('erase', {}).get('mode') == 'hgrad':
            r['erase'] = {'mode': 'flat'}
            r['hsmooth'] = 3
    json.dump(d, open(p, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
