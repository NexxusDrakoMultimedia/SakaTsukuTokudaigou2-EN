import json, os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
s = json.load(open(os.path.join(root, 'translation/art/03578.json'), encoding='utf8'))
s['texture'] = 'ETC_DATA/PL_EDIT.ZAR PL_PT2.TBD#0 (03583) Player Edit labels (scout report)'
s['size'] = [512, 512]
s['regions'] = [r for r in s['regions'] if r['id'] in ('name', 'nickname', 'height', 'foot', 'origin')]
pos = {'name': (90, 262, 50, 27), 'nickname': (90, 302, 54, 27), 'height': (3, 366, 52, 28), 'foot': (3, 402, 70, 28), 'origin': (3, 438, 52, 27)}
for r in s['regions']:
    r['x'], r['y'], r['w'], r['h'] = pos[r['id']]
json.dump(s, open(os.path.join(root, 'translation/art/03583.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
