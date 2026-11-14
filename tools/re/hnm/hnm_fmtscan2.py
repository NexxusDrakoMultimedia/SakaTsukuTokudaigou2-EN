import os, struct, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
names = 'AUTOSAVE BACKUP BPMATCH CHALMODE CSAVE CSAVE3 CSAVE4 DMCLBEDT ENDOPT EVENT EXFLAG EXTRADE FREELOAD HOMETOWN LOAD SCHE0 SCHE1 SONGSAVE SPF_READ VTRLOAD'.split()
SIGA = bytes.fromhex('4365fe7500e35c3e302e')
for n in names:
    d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN'), 'rb').read()
    a = d.find(SIGA)
    cand = [m.start() for m in re.finditer(rb'%s%s\x00\x00\x00\x00Ille', d)]
    lit = struct.unpack_from('<I', d, a + 0x1a6)[0]
    base = lit - cand[0] if len(cand) == 1 else None
    # count literal words pointing at it
    cnt = 0
    if base:
        v = struct.pack('<I', lit)
        cnt = d.count(v)
    # function A start, composer literal pool context
    print(n, hex(a), [hex(c) for c in cand], hex(lit), hex(base) if base else None, 'refs', cnt, 'pool-lit', hex(struct.unpack_from('<I', d, a + 0x1aa)[0]))
