"""aln: assemble the align cave and print its listing (capstone decoded) and size."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import capstone as cs  # noqa: E402
import fontpatch as FP  # noqa: E402

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
A = 0x8c299700
code, sym = FP.align_assembly(A, 0x8c299900)
print('size', len(code), {k: hex(v) for k, v in sym.items()})
for o in range(0, len(code), 2):
    w = struct.unpack_from('<H', code, o)[0]
    i = list(md.disasm(code[o:o + 2], A + o))
    print('+%03x %08x %04x %s' % (o, A + o, w, ('%s %s' % (i[0].mnemonic, i[0].op_str)) if i else '.word %04x' % w))
