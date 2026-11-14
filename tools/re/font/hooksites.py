"""Locate every copy of the tsString layout function (3 code variants) in all overlays and emit the exact patch sites.
Output: hooksites.tsv  (overlay, variant, base, F(entry), wrap_lo, wrap_hi(=draw start), adv_ext, adv_half, adv_full, loop_next, fn_end)
Variant A = MEETING layout (98 overlays, object fields +0x3c/+0x3e/+0x4a, pen x = r10, units = r11)
Variant B = COMM layout    (6 overlays: COMM CON_REP NF_CON PASS_PL J1_REP PL_CON; fields -8: +0x34/+0x36/+0x42, pen x = r11, units = r10)
Variant C = CSAVE3 layout  (1 overlay; B's registers with A's field offsets)
B and C are linked against another 1ST_READ build (see stalecheck.py) and are most likely dead code."""
import csv, os, sys
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')) + '/'
here = os.path.dirname(os.path.abspath(__file__))
def rd(n): return open(R + 'extracted/FLOW_PRG/' + n, 'rb').read()
mb, cm, cs = rd('MEETING.BIN'), rd('COMM.BIN'), rd('CSAVE3.BIN')
MB, CB, SB = 0x8c2d0000, 0x8c2e0000, 0x8c4d0000
A = dict(F=0x8c2de294, d=mb, B=MB, ln=0x240)
Bv = dict(F=0x8c2e0934, d=cm, B=CB, ln=0x190)
Cv = dict(F=0x8c4dd2f0, d=cs, B=SB, ln=0x190)
# offsets relative to F
OFF = {
 'A': dict(wrap_lo=0xa0, wrap_hi=0xe4, adv_ext=0x1f6, adv_half=0x1fc, adv_full=0x20e, loop_next=0x216),
 'B': dict(wrap_lo=0x72, wrap_hi=0xd8, adv_ext=0x14a, adv_half=0x150, adv_full=0x162, loop_next=0x16a),
}
OFF['C'] = OFF['B']
# signatures: (relative offset, length) of the invariant code words used to find the function (pool words excluded)
def sig(v, key):
    F, d, B = v['F'], v['d'], v['B']
    o = OFF['A' if key == 'A' else 'B']
    if key == 'A':
        return d[F - B:F - B + 0x78]          # head (120 B, same as ts_survey)
    return d[F - B:F - B + 0x40]               # B/C head 64 B
sigs = {'A': sig(A, 'A'), 'B': sig(Bv, 'B'), 'C': sig(Cv, 'C')}
core = {'A': A['d'][A['F'] + OFF['A']['adv_ext'] - A['B']:A['F'] + OFF['A']['loop_next'] + 2 - A['B']],
        'B': Bv['d'][Bv['F'] + OFF['B']['adv_ext'] - Bv['B']:Bv['F'] + OFF['B']['loop_next'] + 2 - Bv['B']],
        'C': Cv['d'][Cv['F'] + OFF['C']['adv_ext'] - Cv['B']:Cv['F'] + OFF['C']['loop_next'] + 2 - Cv['B']]}
rows = []
for r in csv.DictReader(open(R + 'build/memmap/overlays.tsv'), delimiter='\t'):
    if not r['base']: continue
    p = R + 'extracted/' + r['dir'] + '/' + r['overlay']
    if not os.path.exists(p): continue
    d = open(p, 'rb').read(); base = int(r['base'], 16)
    for v in 'ABC':
        i = d.find(sigs[v])
        if i < 0: continue
        F = base + i; o = OFF[v]
        ok = d[o['adv_ext'] + i:o['loop_next'] + 2 + i] == core[v]
        rows.append([r['overlay'], r['dir'], v, hex(base), hex(F), hex(F + o['wrap_lo']), hex(F + o['wrap_hi']), hex(F + o['adv_ext']),
                     hex(F + o['adv_half']), hex(F + o['adv_full']), hex(F + o['loop_next']), 'core_ok' if ok else 'CORE_DIFF'])
hdr = ['overlay', 'dir', 'variant', 'base', 'F', 'wrap_lo', 'draw_start', 'adv_ext', 'adv_half', 'adv_full', 'loop_next', 'check']
with open(os.path.join(here, 'hooksites.tsv'), 'w') as f:
    f.write('\t'.join(hdr) + '\n')
    for x in rows: f.write('\t'.join(x) + '\n')
import collections
print(collections.Counter((x[2], x[11]) for x in rows), len(rows))
print([x[0] for x in rows if x[2] != 'A'])
