"""callers of town_short (A) / pref_short (B) in the 20 composer overlays: literal words and bsr instructions"""
import os, struct
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
names = 'AUTOSAVE BACKUP BPMATCH CHALMODE CSAVE CSAVE3 CSAVE4 DMCLBEDT ENDOPT EVENT EXFLAG EXTRADE FREELOAD HOMETOWN LOAD SCHE0 SCHE1 SONGSAVE SPF_READ VTRLOAD'.split()
SIGA = bytes.fromhex('4365fe7500e35c3e302e')
import re
for n in names:
    d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN'), 'rb').read()
    a = d.find(SIGA)
    fmt_off = d.find(b'%s%s\0\0\0\0Ille')
    lit = struct.unpack_from('<I', d, a + 0x1a6)[0]
    base = lit - fmt_off
    A = a - 0x52; B = a + 0x16     # 0x10648 / 0x106b0 relative to sig 0x1069a
    comp = a + 0x90                # 0x1072a
    res = {}
    for nm, fn in (('A', A), ('B', B), ('C', comp)):
        w = struct.pack('<I', base + fn)
        lits = [hex(i) for i in range(0, len(d) - 3, 4) if d[i:i+4] == w]
        bsr = []
        for i in range(0, len(d) - 1, 2):
            op = d[i] | (d[i+1] << 8)
            if op >> 12 == 0xB:
                disp = op & 0xfff
                if disp & 0x800: disp -= 0x1000
                if i + 4 + disp * 2 == fn: bsr.append(hex(i))
        res[nm] = (lits, bsr)
    print(n, hex(base), res)
