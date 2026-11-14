"""s7p_pkg - print packages B C D of groups_v3.json compactly."""
import json, sys
d = json.load(open('build/art/groups_v3.json', encoding='utf8'))
for p in d['packages']:
    if p['key'] in ('B', 'C', 'D'):
        print('==', p['key'], p['name'], p.get('technique'), p.get('screens'))
        for it in p.get('items', []):
            print(it['id'], it.get('source'), it.get('member'), it.get('size'), '|', it.get('ja'), '|', it.get('en') or it.get('wording'), '|', [(c['file'], c['tid'], c.get('installed')) for c in it.get('copies', [])])
