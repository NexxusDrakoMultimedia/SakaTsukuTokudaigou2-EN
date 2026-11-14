"""mn6_dis1st.py ADDR_HEX COUNT_HEX : capstone listing of 1ST_READ.BIN (extracted, original) from address ADDR."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capstone as cs        # noqa: E402
import moneypatch as MP      # noqa: E402

a, n = int(sys.argv[1], 16), int(sys.argv[2], 16)
d = MP.read_extracted('1ST_READ.BIN')
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
o = a - MP.IMG_BASE
for i in md.disasm(d[o:o + n], a):
    print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
