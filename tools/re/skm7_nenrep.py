"""skm7_nenrep.py OFF_HEX COUNT_HEX: capstone listing (skipdata) of extracted FLOW_PRG/NENREP.BIN from file offset OFF.  Read only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capstone as cs        # noqa: E402
import moneypatch as MP      # noqa: E402

o, n = int(sys.argv[1], 16), int(sys.argv[2], 16)
d = MP.read_extracted('FLOW_PRG/NENREP.BIN')
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
md.skipdata = True
for i in md.disasm(bytes(d[o:o + n]), o):
    print('%05x  %-8s %s' % (i.address, i.mnemonic, i.op_str))
