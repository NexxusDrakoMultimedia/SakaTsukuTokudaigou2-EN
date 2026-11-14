"""Survey the per-overlay copies of the tsString layout function (MEETING 0x8c2de294) and its
advance code; also the 'linear text' renderer (slot 0x3d0 loop with add #6 / add #12).
Writes layoutsurvey.tsv.  Signatures are cut from MEETING (reference copy)."""
import struct, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
mb = open(R + r'\extracted\FLOW_PRG\MEETING.BIN', 'rb').read()
MB = 0x8c2d0000
def cut(lo, hi): return mb[lo - MB:hi - MB]
SIG = {
 'head':    cut(0x8c2de294, 0x8c2de30c),   # prologue .. dispatch
 'wrap':    cut(0x8c2de334, 0x8c2de420),   # wrap tests (units counters r11, cells byte +0x3c)
 'adv':     cut(0x8c2de454, 0x8c2de4d4),   # draw call tail + ADVANCE (half 0x8c2de490.., full 0x8c2de4a2..) + loop end
 'adv_core':cut(0x8c2de48a, 0x8c2de4ae),   # just the advance instructions
 'linear':  cut(0x8c2dec3e, 0x8c2dec56),   # glyph->linear loop body up to the jsr
}
rows = []
for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
    if not r['base']: continue
    p = os.path.join(R, 'extracted', r['dir'], r['overlay'])
    if not os.path.exists(p): continue
    d = open(p, 'rb').read(); base = int(r['base'], 16)
    row = {'overlay': r['overlay'], 'base': r['base']}
    for k, s in SIG.items():
        offs = []; i = d.find(s)
        while i >= 0:
            offs.append(i); i = d.find(s, i + 1)
        row[k] = ','.join(hex(base + o) for o in offs) if offs else '-'
    # slot users
    ws = lambda v: any(struct.unpack_from('<H', d, o)[0] >> 12 == 9 and
                       (o + 4 + 2 * (struct.unpack_from('<H', d, o)[0] & 0xff)) + 2 <= len(d) and
                       struct.unpack_from('<H', d, o + 4 + 2 * (struct.unpack_from('<H', d, o)[0] & 0xff))[0] == v
                       for o in range(0, len(d) - 1, 2))
    row['s3ac'] = int(ws(0x3ac)); row['s3b0'] = int(ws(0x3b0)); row['s3b4'] = int(struct.pack('<I', 0x8c1593b4) in d or ws(0x3b4)); row['s3d0'] = int(ws(0x3d0))
    rows.append(row)
cols = ['overlay', 'base', 'head', 'wrap', 'adv', 'adv_core', 'linear', 's3ac', 's3b0', 's3b4', 's3d0']
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layoutsurvey.tsv'), 'w') as f:
    f.write('\t'.join(cols) + '\n')
    for r in rows: f.write('\t'.join(str(r[c]) for c in cols) + '\n')
n = len(rows)
for k in ('head', 'wrap', 'adv', 'adv_core', 'linear'):
    print(k, 'found in', sum(1 for r in rows if r[k] != '-'), 'of', n, ' multi:', sum(1 for r in rows if ',' in r[k]))
print('s3ac', sum(r['s3ac'] for r in rows), 's3b0', sum(r['s3b0'] for r in rows), 's3b4', sum(r['s3b4'] for r in rows), 's3d0', sum(r['s3d0'] for r in rows))
