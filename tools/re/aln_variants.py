"""aln: enumerate the exact instruction-sequence variants of the right-anchor idiom (x = anchor - 12*len) in CAP_SLCT / ENDOPT / EVENT.

    python -I -X utf8 tools/re/aln_variants.py
Normalises registers (L,T,A,W,O) and prints each distinct sequence with its count and the sites.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_scan12 as S12  # noqa: E402
import aln_dis as D  # noqa: E402

groups = {}
for name in ('CAP_SLCT', 'ENDOPT', 'EVENT'):
    d = open(os.path.join(S12.DIR, name + '.BIN'), 'rb').read()
    ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    for off in S12.scan(ws):
        if not S12.near_xstore(ws, off):
            continue
        i = off // 2
        # from 3 words before the mov to the first halfword store @(r0,rn) (0x0n m5) within 14 words
        seq = []
        end = None
        for j in range(i - 3, i + 14):
            seq.append(ws[j])
            if j >= i and ws[j] & 0xF00F == 0x0005:
                end = j
                break
        if end is None:
            continue
        w0 = ws[i]
        T = (w0 >> 8) & 15
        L = (w0 >> 4) & 15
        text = []
        for w in seq:
            t = '%04x' % w
            text.append(t)
        mnems = []
        for w in seq:
            ins = list(D.MD.disasm(struct.pack('<H', w), 0))
            s = '%s %s' % (ins[0].mnemonic, ins[0].op_str) if ins else '.word %04x' % w
            mnems.append(s.replace('r%d' % L, 'L').replace('r%d' % T, 'T'))
        key = ' | '.join(mnems)
        groups.setdefault(key, []).append((name, off))
for k, v in sorted(groups.items(), key=lambda x: -len(x[1])):
    print(len(v), k)
    print('    ', ' '.join('%s:%x' % s for s in v))
