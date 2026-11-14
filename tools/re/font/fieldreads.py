"""Find reads of window fields outside the tsString library: +0x22 (code count, MEETING-type), +0x3c cells, +0x3e advance, +0x4a x-origin.
(mov #FIELD,r0 ; mov.w/mov.b @(r0,Rn),Rm within 2 instructions).  Library range = [head-0x4000, head+0x1000)."""
import struct, csv, os, sys, collections
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
here = os.path.dirname(os.path.abspath(__file__))
sv = {r['overlay']: r for r in csv.DictReader(open(os.path.join(here, 'layoutsurvey.tsv')), delimiter='\t')}
FIELDS = {0x22: 'ncodes', 0x3c: 'cells', 0x3e: 'advance', 0x4a: 'xorg', 0x4c: 'yorg'}
res = collections.defaultdict(list)
for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
    n = r['overlay']
    if not r['base'] or n not in sv or sv[n]['head'] == '-': continue
    d = open(os.path.join(R, 'extracted', r['dir'], n), 'rb').read(); base = int(r['base'], 16)
    h = int(sv[n]['head'], 16); lib = (h - 0x4000, h + 0x1000)
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    for i, w in enumerate(W):
        a = base + 2 * i
        if (w & 0xFF00) == 0xE000 and (w & 0xFF) in FIELDS and not (lib[0] <= a < lib[1]):
            for x in W[i + 1:i + 3]:
                if (x & 0xF00F) in (0x000D, 0x000C):      # mov.w/mov.b @(r0,Rm),Rn
                    res[FIELDS[w & 0xFF]].append('%s:%x' % (n, a)); break
for k, v in res.items():
    print(k, len(v), v[:40])
