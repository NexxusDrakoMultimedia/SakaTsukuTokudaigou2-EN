"""Heuristic scan for code that multiplies by 6 / 12 / 24 (pixel width of N half/full-width chars) outside
the tsString library: patterns  x*6 = (shll Rn; shll2 Rm(copy); add Rm,Rn)  and  x*12 = (...; shll2 again),
 mov #12/#24,Rn followed within 3 instr by muls.w/mul.l.  Output: overlay:addr:kind (candidates only, need manual check)."""
import struct, csv, os, sys, collections
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
here = os.path.dirname(os.path.abspath(__file__))
sv = {r['overlay']: r for r in csv.DictReader(open(os.path.join(here, 'layoutsurvey.tsv')), delimiter='\t')}
out = []
tot = collections.Counter()
for r in csv.DictReader(open(R + r'\build\memmap\overlays.tsv'), delimiter='\t'):
    n = r['overlay']
    if not r['base']: continue
    p = os.path.join(R, 'extracted', r['dir'], n)
    if not os.path.exists(p): continue
    d = open(p, 'rb').read(); base = int(r['base'], 16)
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    # library range to exclude (MEETING-type): head sig .. +0x700 (layout, typewriter, linear)
    lib = None
    if n in sv and sv[n]['head'] != '-':
        h = int(sv[n]['head'], 16); lib = (h - 0x4000, h + 0x1000)
    for i in range(len(W) - 4):
        a = base + 2 * i
        if lib and lib[0] <= a < lib[1]: continue
        w0, w1, w2, w3 = W[i:i + 4]
        # x*6:  mov Rs,Rm ; shll Rn ; shll2 Rm ; add Rm,Rn   (any order of the shll/shll2 pair)
        def is_mov(w): return (w & 0xF00F) == 0x6003
        def is_shll(w): return (w & 0xF0FF) == 0x4000
        def is_shll2(w): return (w & 0xF0FF) == 0x4008
        def is_add(w): return (w & 0xF00F) == 0x300C
        if is_mov(w0):
            m = (w0 >> 8) & 15; s = (w0 >> 4) & 15
            seq = (w1, w2, w3)
            # find shll Rs + shll2 Rm + add Rm,Rs in any order
            if any(is_shll(x) and ((x >> 8) & 15) == s for x in seq) and any(is_shll2(x) and ((x >> 8) & 15) == m for x in seq) and any(is_add(x) and ((x >> 4) & 15) == m and ((x >> 8) & 15) == s for x in seq):
                # check what follows: x12 if another shll2/shll on s within next 2
                nxt = W[i + 4:i + 6]
                k = 'x6'
                if any(is_shll(x) and ((x >> 8) & 15) == s for x in nxt) : k = 'x12'
                elif any(is_shll2(x) and ((x >> 8) & 15) == s for x in nxt): k = 'x24'
                tot[k] += 1; out.append('%s:%x:%s' % (n, a, k))
    for i in range(len(W) - 3):
        a = base + 2 * i
        if lib and lib[0] <= a < lib[1]: continue
        w0 = W[i]
        if (w0 & 0xF000) == 0xE000 and (w0 & 0xFF) in (6, 12, 24):
            rn = (w0 >> 8) & 15
            for x in W[i + 1:i + 4]:
                if (x & 0xF00F) in (0x000F, 0x200F, 0x200E, 0x0007) and ((x >> 4) & 15 == rn or (x >> 8) & 15 == rn):
                    tot['mul%d' % (w0 & 0xFF)] += 1; out.append('%s:%x:mul%d' % (n, a, w0 & 0xFF)); break
print(dict(tot))
open(os.path.join(here, 'widthidioms.txt'), 'w').write('\n'.join(out))
c = collections.Counter(o.split(':')[0] for o in out)
print(c.most_common(30))
