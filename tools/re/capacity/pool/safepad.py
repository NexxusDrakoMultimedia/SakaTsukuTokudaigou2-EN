"""Pool capacity if only alignment fill (pad_mode 'safe') counts as free room beyond the NUL."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import textrepack as R
full = json.load(open(os.path.join(HERE, 'results', 'pools.json')))
tot = dict(pools=0, cap=0, mov_jp=0, slack=0, multi=0, single=0)
res = {}
for source, img, strs, ptrs in load_all('safe'):
    pools, _ = R.find_pools(strs)
    mov = [s for s in strs if R.is_movable(s)]
    res[source] = dict(pools=len(pools), cap=sum(p.cap for p in pools), mov_jp=sum(len(s.raw) + 1 for s in mov),
                       single=sum(1 for p in pools if len(p.home) == 1), largest=max((p.cap for p in pools), default=0))
    for k in ('pools', 'cap', 'mov_jp'):
        tot[k] += res[source][k]
    tot['single'] += res[source]['single']
tot['slack'] = tot['cap'] - tot['mov_jp']
fp = sum(v['pools'] for v in full.values()); fc = sum(v['pool_cap'] for v in full.values()); fs = sum(v['pool_slack'] for v in full.values())
print('safe pad:', tot, ' | full pad: pools', fp, 'cap', fc, 'slack', fs)
json.dump(res, open(os.path.join(HERE, 'results', 'safepad.json'), 'w'))
for n in ('MEETING', 'NEWS', 'HELP', 'TRAINING', 'EVENT', 'GAME', 'DRAFT'):
    s = 'FLOW_PRG/%s.BIN' % n
    print(n, 'safe', res[s]['pools'], res[s]['cap'], res[s]['cap'] - res[s]['mov_jp'], '| full', full[s]['pools'], full[s]['pool_cap'], full[s]['pool_slack'])
