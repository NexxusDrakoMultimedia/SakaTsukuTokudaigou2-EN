"""Count call sites of the 'linear text' function (string -> 4bpp bitmap via slot 0x3d0) and
of the layout/draw function per overlay (MEETING-type copies; function entry = signature offset - const)."""
import struct, csv, os, sys
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
here = os.path.dirname(os.path.abspath(__file__))
sv = {r['overlay']: r for r in csv.DictReader(open(os.path.join(here, 'layoutsurvey.tsv')), delimiter='\t')}
LIN_OFF = 0x8c2dec3e - 0x8c2debe0       # linear sig offset from function start (MEETING)
tot = 0
for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
    n = r['overlay']
    if not r['base'] or n not in sv or sv[n]['linear'] == '-' or sv[n]['head'] == '-': continue
    d = open(os.path.join(R, 'extracted', r['dir'], n), 'rb').read(); base = int(r['base'], 16)
    fn = int(sv[n]['linear'], 16) - LIN_OFF
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    cnt = 0
    for i, w in enumerate(W):
        a = base + i * 2
        if (w >> 12) == 0xB and ((a + 4 + 2 * ((w & 0xFFF) - (0x1000 if w & 0x800 else 0))) & 0xFFFFFFFF) == fn: cnt += 1
    lit = d.count(struct.pack('<I', fn))
    tot += cnt + lit
    print('%-12s linear_fn=%x bsr_calls=%d literal_refs=%d' % (n, fn, cnt, lit))
print('total', tot)
