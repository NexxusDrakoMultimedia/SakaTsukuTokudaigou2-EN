"""svfmt_mkimg.py NAME... : build combined images (1ST_READ at 0x8c010000 + overlay at its base)
for Ghidra, into build/svfmt/NAME.img (base 0x8c010000).  Read-only on extracted/."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = {'AUTOSAVE': 0x8c8d0000, 'SONGSAVE': 0x8c8d0000, 'CSAVE': 0x8c4d0000, 'CSAVE3': 0x8c4d0000,
         'CSAVE4': 0x8c4d0000, 'N_ENTRY': 0x8c8d0000, 'LOAD': None}
def main():
    fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    os.makedirs(os.path.join(ROOT, 'build', 'svfmt'), exist_ok=True)
    for n in sys.argv[1:]:
        ov = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN'), 'rb').read()
        base = BASES[n]
        off = base - 0x8c010000
        img = bytearray(fr) + bytes(off - len(fr)) + ov
        p = os.path.join(ROOT, 'build', 'svfmt', n + '.img')
        open(p + '.tmp', 'wb').write(img); os.replace(p + '.tmp', p)
        print(n, hex(base), len(img))
main()
