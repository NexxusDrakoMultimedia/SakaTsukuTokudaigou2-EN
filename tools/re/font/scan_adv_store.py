"""Find stores to window+0x3e (advance) : 'mov #62,r0' (0xE03E) within 6 words before 'mov.b Rm,@(r0,Rn)'.
For each, report the nearest preceding 'mov #imm,Rm' (imm).  Variant B overlays use +0x36 (54).
python -I -X utf8 tools/re/font/scan_adv_store.py"""
import glob, os, struct, collections
cnt = collections.Counter(); per = {}
for f in sorted(glob.glob('extracted/FLOW_PRG/*.BIN')) + ['extracted/ATFIRST/HELP.BIN']:
    d = open(f, 'rb').read(); n = len(d) // 2
    W = struct.unpack('<%dH' % n, d[:n * 2])
    name = os.path.basename(f)
    ofs = 54 if name in ('COMM.BIN','CON_REP.BIN','NF_CON.BIN','PASS_PL.BIN','J1_REP.BIN','PL_CON.BIN') else 62
    for i, w in enumerate(W):
        if w == 0xE000 | ofs:     # mov #ofs,r0
            for j in range(i + 1, min(i + 8, n)):
                x = W[j]
                if x & 0xF00F == 0x0004:          # mov.b Rm,@(R0,Rn)
                    m = (x >> 4) & 15; nn = (x >> 8) & 15
                    val = None
                    for k in range(j - 1, max(j - 16, 0), -1):
                        y = W[k]
                        if y & 0xF000 == 0xE000 and (y >> 8) & 15 == m:
                            val = y & 0xFF; break
                        if y & 0xF00F == 0x6003 and (y >> 8) & 15 == m:   # mov Rm',Rm : unknown source
                            val = 'reg'; break
                    cnt[(ofs, val)] += 1
                    per.setdefault(name, []).append((hex(i * 2), val)); break
print(cnt)
for k, v in per.items():
    print(k, v)
