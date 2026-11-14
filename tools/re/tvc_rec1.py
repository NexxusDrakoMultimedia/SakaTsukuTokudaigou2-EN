"""tvc_rec1.py : TV_EVENT records: the two money pieces of the replaced card routine become dead (en cleared, skip), atomic rewrite."""
import json, os
p = 'translation/FLOW_PRG__TV_EVENT.BIN.jsonl'
raw = open(p, 'rb').read().decode('utf8')
nl = '\r\n' if '\r\n' in raw else '\n'
lines = raw.split(nl)
tail = lines[-1] == ''
if tail:
    lines = lines[:-1]
out = []
dead = {'FLOW_PRG/TV_EVENT.BIN#b624', 'FLOW_PRG/TV_EVENT.BIN#b62c'}
n = 0
for ln in lines:
    r = json.loads(ln)
    assert json.dumps(r, ensure_ascii=False, separators=(',', ':')) == ln, ln[:60]
    if r['id'] in dead:
        r['en'] = ''
        r['skip'] = True
        n += 1
    out.append(json.dumps(r, ensure_ascii=False, separators=(',', ':')))
assert n == 2
tmp = p + '.tmp'
open(tmp, 'wb').write((nl.join(out) + (nl if tail else '')).encode('utf8'))
os.replace(tmp, p)
print('ok', n)
