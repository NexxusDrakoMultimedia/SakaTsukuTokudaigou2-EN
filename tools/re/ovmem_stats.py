"""ovmem: aggregate numbers for docs/expansion/overlay-memory.md from build/memmap/overlays.tsv (read-only)."""
import csv
rows = [r for r in csv.DictReader(open('build/memmap/overlays.tsv'), delimiter='\t') if r['dir'] == 'FLOW_PRG' and r['heap_bytes']]
print('overlays with heap', len(rows))
tight = []
for r in rows:
    t = int(r['text_ja_bytes'] or 0); c = int(r['append_cons'] or 0); h = int(r['heap_bytes'])
    if t and c < 1.5 * t: tight.append((r['overlay'], t, c, h, int(r['bss_pad_cost'] or 0)))
print('cons < 1.5 x JA text:', tight)
print('sum bss pad all', sum(int(r['bss_pad_cost'] or 0) for r in rows))
print('min/median/max heap', min(int(r['heap_bytes']) for r in rows), sorted(int(r['heap_bytes']) for r in rows)[len(rows)//2], max(int(r['heap_bytes']) for r in rows))
# raising the slot count by one: which overlays have a following slot span (base+count) below slot 9 end
import collections
c = collections.Counter()
for r in rows:
    se = int(r['slot_end'], 16)
    c['ends_at_or_before_0x8cad0000' if se <= 0x8cad0000 else 'reaches_slot9_or_beyond'] += 1
print(c)
