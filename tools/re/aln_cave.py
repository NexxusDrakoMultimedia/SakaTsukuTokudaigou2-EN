"""aln: print the current font cave (fontpatch.cave_bytes) disassembled, with optional --scale."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import capstone as cs  # noqa: E402
import fontpatch as FP  # noqa: E402

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
ct = FP.placement()
code = FP.cave_bytes(ct, scale='--scale' in sys.argv)
print('cave %#x table %#x size %d' % (ct[0], ct[1], len(code)))
for o in range(0, len(code), 2):
    w = struct.unpack_from('<H', code, o)[0]
    i = list(md.disasm(code[o:o + 2], ct[0] + o))
    t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
    print('+%02x %08x %04x %s' % (o, ct[0] + o, w, t))
