"""Print the CLUBEDIT explanation messages (en + ja) in pool order.  usage: python -I -X utf8 tools/re/cw_showmsg.py [k ...]"""
import json, struct, sys
recs = {}
for l in open('translation/FLOW_PRG__CLUBEDIT.BIN.jsonl', encoding='utf8'):
    r = json.loads(l); recs[int(r['id'].split('#')[1], 16)] = r
d = open('extracted/FLOW_PRG/CLUBEDIT.BIN', 'rb').read()
ks = [int(a) for a in sys.argv[1:]] or range(1, 55)
for k in ks:
    v = struct.unpack_from('<I', d, 0x1eb8c + 4*k)[0] - 0x8c2d0000
    r = recs[v]
    print('---', k, r['id'], 'max', r.get('max_bytes'), 'len', len(r['en'].encode('cp932', 'replace')))
    print(r['en']); print('   JA:', r['ja'].replace('\n', ' / '))
