"""Dump the pool-index -> message pointer table at CLUBEDIT 0x1eb8c (and neighbours) with the first ja line of each message."""
import sys, struct, json
d = open('extracted/FLOW_PRG/CLUBEDIT.BIN', 'rb').read()
recs = {}
for l in open('translation/FLOW_PRG__CLUBEDIT.BIN.jsonl', encoding='utf8'):
    r = json.loads(l); recs[int(r['id'].split('#')[1], 16)] = r
start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x1eb8c
for i in range(-2, 64):
    o = start + 4*i
    v = struct.unpack_from('<I', d, o)[0]
    f = v - 0x8c2d0000
    r = recs.get(f)
    t = r['ja'].split('\n')[0][:30] if r else ''
    en = r['en'].split(' ')[0] if r else ''
    print(i, hex(o), hex(v), t, '|', en)
