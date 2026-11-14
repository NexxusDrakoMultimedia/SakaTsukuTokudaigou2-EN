"""build adversarial scenario inputs into <dir>: tdb/ members/  (python -I -X utf8 vp_mkscen.py <dir>)"""
import sys, os, json, random
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib
out = sys.argv[1]
os.makedirs(out + '/tdb', exist_ok=True)
def load(src):
    return {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(ROOT, 'translation', src.replace('/', '__') + '.jsonl'), encoding='utf8')}
sel = {}
def put(src, rid, en):
    r = load_cache.setdefault(src, load(src))[rid]; r = dict(r); r['en'] = en; sel.setdefault(src, {})[rid] = r
load_cache = {}
# NEWS: 21-ref string made long + 6 neighbours shortened (frees space); another 21-ref string short in place
put('FLOW_PRG/NEWS.BIN', 'FLOW_PRG/NEWS.BIN#117102', ('Long English sentence that is much longer than the Japanese slot ' * 2).strip())
put('FLOW_PRG/NEWS.BIN', 'FLOW_PRG/NEWS.BIN#115f27', 'Group stage over.')
nw = sorted(load('FLOW_PRG/NEWS.BIN').values(), key=lambda r: int(r['id'].split('#')[1], 16))
k = [i for i, r in enumerate(nw) if r['id'].endswith('#117102')][0]
print('NEWS neighbours', [(r['id'].split('#')[1], r['max_bytes'], r['refs']) for r in nw[k-3:k+6]])
for r in nw[k-3:k+0] + nw[k+1:k+5]:
    put('FLOW_PRG/NEWS.BIN', r['id'], 'OK')
# EVENT: 18-ref string long, no spare room -> must FAIL and keep Japanese
put('FLOW_PRG/EVENT.BIN', 'FLOW_PRG/EVENT.BIN#c5d54', 'X' * 200)
# MEETING: boundary: max_bytes-1 chars fits exactly; another one max_bytes chars (1 byte over) must fail
m = load('FLOW_PRG/MEETING.BIN')
ids = list(m)
a, b = m[ids[0]], m[ids[1]]
put('FLOW_PRG/MEETING.BIN', ids[0], 'A' * (a['max_bytes'] - 1))
put('FLOW_PRG/MEETING.BIN', ids[1], 'B' * b['max_bytes'])
print('MEETING exact-fit', ids[0], a['max_bytes'], ' one-over', ids[1], b['max_bytes'])
# PL_EDIT (no-BSS) overflow, for --append-safe runs
p = load('FLOW_PRG/PL_EDIT.BIN')
cand = [r for r in p.values() if r['max_bytes'] >= 20 and r['refs'] == 1][:3]
for i, r in enumerate(cand):
    put('FLOW_PRG/PL_EDIT.BIN', r['id'], 'Overflowing text number %d ' % i + 'z' * 150)
for src, d in sel.items():
    with open('%s/tdb/%s.jsonl' % (out, src.replace('/', '__')), 'w', encoding='utf8') as f:
        for r in d.values(): f.write(json.dumps(r, ensure_ascii=False) + '\n')
# members
random.seed(7)
def member_swap(cont, name, newplain, sub=None):
    p = os.path.join(out, 'members', *cont.split('/'))
    os.makedirs(p, exist_ok=True)
    open(os.path.join(p, name), 'wb').write(newplain)
def members(cont):
    d = open(os.path.join(ROOT, 'extracted', *cont.split('/')), 'rb').read()
    ms, t = bzlib.parse_archive(d)
    return ms
ms = members('GAME/KSPAPET.ZAR')
for m_ in ms[:6]: print('KSPAPET', m_.name, m_.method, m_.orig_size if hasattr(m_, 'orig_size') else '')
bzw = [m_ for m_ in ms if m_.method == '-bzw-'][0]; bz = [m_ for m_ in ms if m_.method == '-bz--'][0]
member_swap('GAME/KSPAPET.ZAR', bzw.name, bzw.extract() + bytes(random.randrange(256) for _ in range(3000)))
member_swap('GAME/KSPAPET.ZAR', bz.name, bz.extract()[:len(bz.extract()) // 2])
ms = members('GAME/STAFFLST.ZAR')
import collections
cnt = collections.Counter(x.name for x in ms)
print('ALLPNAME dup names', sum(1 for v in cnt.values() if v>1), 'of', len(ms))
m0 = [x for x in ms if cnt[x.name] == 1 and x.method == '-bz--'][0]
member_swap('GAME/STAFFLST.ZAR', m0.name, m0.extract() + bytes(random.randrange(256) for _ in range(150000)))   # container grows past its extent
ms = members('ETC_DATA/CH_DANI.ZAR')
cnt = collections.Counter(x.name for x in ms)
nc = [x for x in ms if cnt[x.name] == 1 and x.method == '-nc--'][0]
member_swap('ETC_DATA/CH_DANI.ZAR', nc.name, nc.extract() + b'\x5a' * 7000)
print('done')
