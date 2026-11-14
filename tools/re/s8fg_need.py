"""s8fg: hwptr records (all, with pointers) whose English does NOT fit the original slot = the ones that must move in any plan; per overlay count + total; also flags those that look like array bases (neighbour recarr at +-S or ja == dummy)."""
import glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tot = 0; allp = 0; base_like = []
for jp in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    rel = os.path.basename(jp)[:-6].replace('__', '/')
    recs = [json.loads(l) for l in open(jp, encoding='utf-8') if l.strip()]
    arr = {}
    for r in recs:
        if r.get('fmt') == 'recarr':
            m = re.search(r'S=(\d+)', r.get('ctx', ''))
            if m:
                arr.setdefault(int(m.group(1)), set()).add(int(r['id'].split('#')[1], 16))
    n = 0
    for r in recs:
        if r.get('fmt') != 'hwptr' or not r.get('refs') or not r.get('en') or 'hwpool' in r.get('ctx', ''):
            continue
        allp += 1
        need = len(r['en'].encode('cp932', 'replace')) + 1 > (r.get('slot') or r['max_bytes'])
        off = int(r['id'].split('#')[1], 16)
        bl = any(off + S in o or off - S in o for S, o in arr.items()) or r['ja'] == 'ﾀﾞﾑｲ'
        if need:
            n += 1
            if bl:
                base_like.append((rel, r['id'], r['en'], r['ja']))
    tot += n
print('relocatable hwptr records with English:', allp, ' of which do not fit their slot (must move):', tot)
print('must-move AND look like array base:', len(base_like), base_like[:10])
