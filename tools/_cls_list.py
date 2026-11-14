import json,sys
m=json.load(open('build/tex/sheets/sheet_map.json'))
for s in ('sheet_0024','sheet_0025','sheet_0026','sheet_0027'):
    d=m['sheets'][s]
    print(s,d['width'],d['height'],len(d['items']))
    for i in d['items']:
        print(' ',i['n'],i['id'],i['container'],i['x'],i['y'],i['src_w'],i['src_h'])
