"""Find stores of small immediates into text-window byte fields, e.g.  mov #imm,Rm ; mov #FIELD,r0 ; mov.b Rm,@(r0,Rn)
usage: fieldstores.py  -> histogram per field for the fields 0x3c (cells/line), 0x3d (rows), 0x3e (advance), 0x3f (line height)
(MEETING-type object layout; COMM-type layout is 8 lower: 0x34..0x37)"""
import struct, csv, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
survey = {}
for r in csv.DictReader(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layoutsurvey.tsv')), delimiter='\t'):
    survey[r['overlay']] = r
FIELDS = {0x3c: 'cells', 0x3d: 'rows', 0x3e: 'advance', 0x3f: 'lineh'}
hist = {f: collections.Counter() for f in FIELDS}
where = {f: collections.defaultdict(list) for f in FIELDS}
for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
    if not r['base']: continue
    n = r['overlay']
    if n not in survey or survey[n]['head'] == '-': continue
    p = os.path.join(R, 'extracted', r['dir'], n)
    d = open(p, 'rb').read(); base = int(r['base'], 16)
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    for i, w in enumerate(W):
        if (w & 0xFF00) == 0xE000 and (w & 0xFF) in FIELDS:           # mov #FIELD,r0
            f = w & 0xFF
            for j in range(i + 1, min(i + 4, len(W))):
                v = W[j]
                if (v & 0xF00F) == 0x0004:                           # mov.b Rm,@(r0,Rn)
                    m = (v >> 4) & 15
                    for k in range(j - 1, max(j - 12, 0), -1):       # nearest preceding write of Rm
                        u = W[k]
                        if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                            imm = u & 0xFF
                            imm = imm - 256 if imm > 127 else imm
                            hist[f][imm] += 1; where[f][imm].append('%s:%x' % (n, base + i * 2)); break
                    break
for f in FIELDS:
    print('field +0x%x (%s): %s' % (f, FIELDS[f], dict(sorted(hist[f].items()))))
for f in (0x3e,):
    for imm, w in sorted(where[f].items()):
        print('  adv', imm, w[:12])
