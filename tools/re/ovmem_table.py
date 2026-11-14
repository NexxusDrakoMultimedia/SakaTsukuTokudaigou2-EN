"""ovmem: print the per-overlay growth table (markdown) from build/memmap/overlays.tsv (read-only).
usage: python -I -X utf8 tools/re/ovmem_table.py > table.md"""
import csv
rows = list(csv.DictReader(open('build/memmap/overlays.tsv'), delimiter='\t'))
special = {'GAME.BIN': 'stub zeroes [?,_end): needs stub patch', 'ESTABLIS.BIN': 'stub ignores _end, private area',
           'MOVIE.BIN': 'stub adds 0x400, title-time', 'MOVIE_BG.BIN': 'stub adds 0x400, title-time', 'LOADBAR.BIN': 'non-slot base'}
print('| overlay | load addr | file B | slots | BSS B | heap B (after BSS) | safe growth B (heap-limited) | hard limit B | extra disc B (BSS pad + growth) | JA text B | note |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for r in rows:
    if r['dir'] != 'FLOW_PRG' or r['overlay'] == 'SECBND.BIN':
        continue
    n = r['overlay']
    cons, hard = r['append_cons'], r['append_hard']
    if not r['heap_bytes']:
        cons = hard = '-'
        note = 'slot span unknown (base not slot aligned)'
        pad = '-'
    else:
        pad = str(int(r['bss_pad_cost'] or 0) + int(cons or 0))
        note = special.get(n, '')
        if n in ('ESTABLIS.BIN',): cons = hard = '0'; pad = '-'
    print('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
        n.replace('.BIN', ''), r['base'], r['file_size'], r['desc_count'], r['bss_bytes'] or '0', r['heap_bytes'] or '-',
        cons, hard, pad, r['text_ja_bytes'] or '-', note))
