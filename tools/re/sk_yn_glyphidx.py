import os, sys, struct, re
roots = ['extracted', 'build/unpacked', 'build/emu']
pats = {}
def seqs(ws, wi, we):
    out = {}
    for sp in ([], [0], [0x2020], [0x2020,0x2020], [0x8020], [0x8020,0x8020], [0x2020|0x8000]):
        out['ha_i_'+str(sp)] = [wi[0]] + sp + [wi[1]]
    return out
ha, i, e = 328, 285, 289
cands = {}
for sp in ([], [0], [0x2020], [0x2020, 0x2020], [0x8020], [0x8020, 0x8020]):
    cands['hai%s' % sp] = [ha] + sp + [i]
cands['iie'] = [i, i, e]
res = []
for root in roots:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                d = open(p, 'rb').read()
            except Exception:
                continue
            for name, s in cands.items():
                for endian in ('<', '>'):
                    pat = b''.join(struct.pack(endian + 'H', x) for x in s)
                    for m in re.finditer(re.escape(pat), d):
                        res.append((p, name, endian, hex(m.start())))
for r in res[:80]:
    print(*r)
print(len(res))
