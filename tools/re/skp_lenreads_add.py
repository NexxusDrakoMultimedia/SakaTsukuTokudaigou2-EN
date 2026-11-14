"""skp (skeptic): find reads of the panel length fields (obj+64..144 step 8) that use the `mov #K,rN ; add rO,rN ; mov.x @rN,rM` form
(the setters WRITE with it: `mov #72,r1 ; add r14,r1 ; mov.l r0,@r1`), which tools/re/aln_lenreads.py (r0 indexed only) cannot see.

    python -I -X utf8 tools/re/skp_lenreads_add.py OVERLAY [START END]       (hex file offsets; default the whole image)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]
d = open(os.path.join(HERE, '..', '..', 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else len(d)
K = set(range(64, 148, 8))
n = 0
for i in range(lo // 2, min(hi // 2, len(ws) - 6)):
    w = ws[i]
    val = None
    if w >> 12 == 0xE and (w & 0xFF) in K:
        val = w & 0xFF
        rn = (w >> 8) & 15
    elif w >> 12 == 0x9:
        at = i * 2
        lit = at + 4 + (w & 0xFF) * 2
        v = struct.unpack_from('<h', d, lit)[0] if lit + 2 <= len(d) else None
        if v in K:
            val = v
            rn = (w >> 8) & 15
    if val is None:
        continue
    for j in range(i + 1, i + 5):
        a = ws[j]
        if a & 0xF00F == 0x300C and (a >> 8) & 15 == rn:          # add rm,rn
            for k in range(j + 1, j + 4):
                b = ws[k]
                if b & 0xF00C == 0x6000 and (b & 3) != 3 and (b >> 4) & 15 == rn:     # mov.b/w/l @rn,rm   (6mn0/1/2)
                    print('%#x: read len+%d via %s @r%d -> r%d (add at %#x)' % (k * 2, val, {0: 'mov.b', 1: 'mov.w', 2: 'mov.l'}[b & 3], rn, (b >> 8) & 15, j * 2))
                    n += 1
                    break
            break
print(name, 'reads found', n)
