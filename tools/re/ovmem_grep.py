"""ovmem: find 32-bit words in FLOW_PRG/ATFIRST/root images that equal given values (read-only). usage: ovmem_grep.py HEX..."""
import glob, struct, sys
vals = [int(h, 16) for h in sys.argv[1:]]
for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN') + glob.glob('extracted/ATFIRST/*.BIN') + ['extracted/1ST_READ.BIN']):
    D = open(p, 'rb').read()
    for v in vals:
        pat = struct.pack('<I', v)
        i = D.find(pat)
        hits = []
        while i >= 0 and len(hits) < 5:
            hits.append(hex(i)); i = D.find(pat, i + 1)
        if hits: print(p, hex(v), hits)
