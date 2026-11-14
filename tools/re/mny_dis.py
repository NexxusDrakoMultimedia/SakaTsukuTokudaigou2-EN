"""mny_dis.py : capstone listing of a range of an extracted overlay.   mny_dis.py REL BASE START END   (hex numbers; offsets = file offsets)"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capstone as cs
import moneypatch as MP
rel, base, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16)
d = MP.read_extracted(rel)
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
for i in md.disasm(d[a:b], base + a):
    print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
