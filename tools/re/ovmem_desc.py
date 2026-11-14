"""ovmem: raw descriptor bytes (slot idx, count byte incl. 0x80 flag, heap word) of overlays from build/memmap/overlays.tsv (read-only).
usage: ovmem_desc.py [NAME...]"""
import csv, struct, sys
rows = list(csv.DictReader(open('build/memmap/overlays.tsv'), delimiter='\t'))
names = set(a.upper() for a in sys.argv[1:])
for r in rows:
    n = r['overlay'].replace('.BIN', '')
    if r['dir'] != 'FLOW_PRG' or (names and n not in names): continue
    D = open('extracted/FLOW_PRG/' + r['overlay'], 'rb').read()
    base = int(r['base'], 16); d = int(r['desc'], 16) - base
    if not (0 <= d < len(D) - 16): continue
    print('%-10s base %s desc +%#x byte0=%d byte1=%#x w4=%#x w8..=%s' % (n, r['base'], d, D[d], D[d+1], struct.unpack_from('<I', D, d+4)[0], ' '.join('%08x' % struct.unpack_from('<I', D, d+8+4*i)[0] for i in range(4))))
