"""s8ha: assemble the align cave and print its size and symbols."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fontpatch as FP
ct = FP.placement()
code, sym = FP.align_assembly(FP.align_address(), ct[1], ct[0])
print(len(code), 'bytes of', FP.ALIGN_RESERVE)
print({k: hex(v) for k, v in sym.items()})
