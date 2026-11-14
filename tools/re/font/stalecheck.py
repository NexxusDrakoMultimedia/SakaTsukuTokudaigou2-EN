"""Heuristic: for each overlay, take literals that are jsr targets (mov.l @(pc),Rn ... jsr @Rn within 6 instr) and point into
1ST_READ (0x8c010000-0x8c2b0000).  A real function entry normally follows an 'rts' + delay slot (word at t-4 == 0x000b) or a
pool/padding; mid-function addresses do not.  Report the fraction of 'entry-like' targets per overlay."""
import struct, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sh4dis import *
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')) + '/'
first = open(R + 'extracted/1ST_READ.BIN', 'rb').read(); FB = 0x8c010000
def w16(a):
    o = a - FB
    return struct.unpack_from('<H', first, o)[0] if 0 <= o < len(first) - 1 else None
def entry_like(t):
    # previous instruction pair: rts ; delay   -> word at t-4 == 0x000b ; or jmp/bra unconditional ; or t aligned after literal pool (rare)
    p = w16(t - 4); q = w16(t - 2)
    return p == 0x000B or (p is not None and (p & 0xF0FF) == 0x402B) or (p is not None and (p >> 12) == 0xA) or q == 0x0000 or q == 0x0009 and p == 0x000B
res = []
for r in csv.DictReader(open(R + 'build/memmap/overlays.tsv'), delimiter='\t'):
    if not r['base']: continue
    p = R + 'extracted/' + r['dir'] + '/' + r['overlay']
    if not os.path.exists(p): continue
    img = Image(open(p, 'rb').read(), int(r['base'], 16)); d = img.d
    W = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    tg = {}
    for i in range(len(W) - 1):
        w = W[i]
        if w >> 12 == 0xD:
            a = img.base + 2 * i; ea = (a & ~3) + 4 + 4 * (w & 0xff); v = img.u32(ea); rn = (w >> 8) & 15
            if v is not None and FB <= v < 0x8c2b0000 and not (v & 1):
                for j in range(i + 1, min(i + 7, len(W))):
                    if W[j] == (0x400B | (rn << 8)): tg[v] = 1; break
    n = len(tg); good = sum(1 for t in tg if entry_like(t))
    res.append((r['overlay'], n, good))
res.sort(key=lambda x: (x[2] / x[1]) if x[1] else 1)
for o, n, g in res[:14]: print('%-12s targets=%d entry_like=%d (%.0f%%)' % (o, n, g, 100.0 * g / n if n else 0))
import statistics
fr = [g / n for o, n, g in res if n >= 5]
print('median fraction over overlays:', statistics.median(fr))
