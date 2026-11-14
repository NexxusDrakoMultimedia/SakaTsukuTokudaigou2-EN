"""ovmem: print selected columns of build/memmap/overlays.tsv (read-only). usage: ovmem_rows.py [NAME...]"""
import csv, sys
rows = list(csv.DictReader(open('build/memmap/overlays.tsv'), delimiter='\t'))
names = set(a.upper() for a in sys.argv[1:])
cols = ['overlay','dir','file_size','base','desc_count','file_end','end_value','bss_bytes','slot_end','heap_bytes','tail_after_file','append_hard','append_cons','bss_pad_cost','text_ja_bytes']
print('\t'.join(cols))
for r in rows:
    if not names or r['overlay'].replace('.BIN','') in names:
        print('\t'.join(r[c] for c in cols))
