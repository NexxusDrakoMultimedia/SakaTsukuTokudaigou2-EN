"""Write patched copies (representatives) for the Ghidra cross-check: build/font/patched/*.  Never touches extracted/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpatch as FP
out = os.path.join(FP.ROOT, 'build', 'font', 'patched')
os.makedirs(out, exist_ok=True)
code, lst, sym = FP.assemble_cave()
for s in FP.scan_all():
    if s['name'] in ('MEETING.BIN', 'COMM.BIN', 'CSAVE3.BIN') and 'ATFIRST' not in s['iso']:
        d = open(os.path.join(FP.ROOT, 'extracted', s['iso']), 'rb').read()
        open(os.path.join(out, s['name']), 'wb').write(FP.apply_hooks(d, s, sym))
k = open(os.path.join(FP.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
open(os.path.join(out, '1ST_READ.BIN'), 'wb').write(FP.patch_1st_read(k))
print('written', os.listdir(out))
