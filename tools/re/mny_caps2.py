"""mny_caps2.py : context of the 99,999,999 literal (the 10^8-1 money cap) in an overlay: who loads it and what follows.
    python -I -X utf8 tools/re/mny_caps2.py FLOW_PRG/GETREP.BIN"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capstone as cs
import moneypatch as MP

rel = sys.argv[1]
want = int(sys.argv[2], 0) if len(sys.argv) > 2 else 99999999
d = MP.read_extracted(rel)
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
lits = [off for off in range(0, len(d) - 3, 4) if struct.unpack_from('<I', d, off)[0] == want]
print(rel, 'literals at', [hex(x) for x in lits])
for lit in lits[:3]:
    # find mov.l @(disp,pc),Rn that loads it
    for a in range(max(0, lit - 1024), lit, 2):
        w = struct.unpack_from('<H', d, a)[0]
        if (w >> 12) == 0xD and (((a + 4) & ~3) + (w & 0xFF) * 4) == lit:
            print('  loaded at %#x by %s' % (a, 'mov.l r%d' % ((w >> 8) & 15)))
            lo = max(0, a - 24)
            for i in md.disasm(d[lo:a + 40], lo):
                print('    %05x %s %s' % (i.address, i.mnemonic, i.op_str))
            break
