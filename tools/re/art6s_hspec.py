import sys, json
# usage: art6s_hspec.py ID dilate region_id... -> tools/re/art6/<ID>h.json with hfill plate erase on those regions
tid, dil, ids = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
s = json.load(open('tools/re/art6/%s.json' % tid, encoding='utf8'))
for r in s['regions']:
    if r['id'] in ids:
        e = r['erase']
        e['dilate'] = dil; e['fill'] = 'hfill'
json.dump(s, open('tools/re/art6/%sh.json' % tid, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
