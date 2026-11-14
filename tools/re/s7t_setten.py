"""s7t: set `en` of records by id (read-modify-write per file, atomic replace, backup of the first version under build/s7/bak)."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_common as C
SETS = {
    'FLOW_PRG/SCHE0.BIN#396c8': 'Trip %d man , Host %d man',
    'FLOW_PRG/SCHE1.BIN#396c8': 'Trip %d man , Host %d man',
    'FLOW_PRG/RECON.BIN#21260': '%d:%4d:%d man %d yr',
    'FLOW_PRG/GETREP.BIN#26c28': 'Ratio: %d00 man / %d = %f',
    'FLOW_PRG/SPT_CLUB.BIN#c50c': 'Ratio: %d00 man / %d = %f',
    'FLOW_PRG/MEETING.BIN#9c954': 'Pay:%d00 man up:%d man',
}
import collections
byfile = collections.defaultdict(dict)
for i, en in SETS.items():
    byfile[i.split('#')[0]][i] = en
for src, d in byfile.items():
    p = os.path.join(ROOT, 'translation', src.replace('/', '__') + '.jsonl')
    raw = open(p, 'rb').read().decode('utf8')
    bak = os.path.join(ROOT, 'build', 's7', 'bak', os.path.basename(p) + '.s7t')
    if not os.path.exists(bak):
        open(bak, 'wb').write(raw.encode('utf8'))
    out = []; n = 0
    for l in raw.split('\n'):
        if l.strip():
            o = json.loads(l)
            if o['id'] in d:
                en = d[o['id']]
                assert len(C.encode_text(en)) + 1 <= o['max_bytes'], (o['id'], en)
                o['en'] = en; n += 1
                l = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
        out.append(l)
    assert n == len(d), (src, n)
    tmp = p + '.s7t.tmp'
    open(tmp, 'wb').write('\n'.join(out).encode('utf8'))
    os.replace(tmp, p)
    print(src, n)
