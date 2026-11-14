"""Numbers quoted in docs/memory-map.md, computed from build/memmap/overlays.tsv + the dumps.
Run:  python -I -X utf8 tools/re/capacity/memmap/summary.py   (after tools/memmap.py all)"""
import csv
import os
import statistics
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import memmap as m  # noqa: E402

rows = list(csv.DictReader(open(os.path.join(ROOT, 'build', 'memmap', 'overlays.tsv'), encoding='utf-8'), delimiter='\t'))
print('rows', len(rows))
ov = [r for r in rows if r['stub']]
print('overlays with decoded stub', len(ov), Counter(r['stub'] for r in ov))
print('FLOW_PRG', sum(1 for r in ov if r['dir'] == 'FLOW_PRG'), 'ATFIRST', sum(1 for r in ov if r['dir'] == 'ATFIRST'))
print('not overlay rows', [(r['dir'], r['overlay'], r['note']) for r in rows if not r['stub']])
sl = [r for r in ov if r['slot_end']]
print('with slot span', len(sl), ' without', [(r['overlay'], r['base']) for r in ov if not r['slot_end']])
print('slot-aligned', sum(1 for r in ov if r['slot_aligned'] == '1'), 'not', [r['overlay'] for r in ov if r['slot_aligned'] != '1'])
print('desc_count distribution', sorted(Counter(int(r['desc_count']) for r in sl).items()))
H = [int(r['heap_bytes']) for r in sl]
print('heap bytes min/median/max', min(H), statistics.median(H), max(H))
print('heap < 1 MiB:', sorted((int(r['heap_bytes']), r['overlay']) for r in sl if int(r['heap_bytes']) < 1 << 20))
bss = [r for r in sl if r['has_bss'] == '1']
nob = [r for r in sl if r['has_bss'] == '0']
print('has_bss', len(bss), 'no bss', len(nob), 'bss bytes total', sum(int(r['bss_bytes']) for r in bss),
      'max', max((int(r['bss_bytes']), r['overlay']) for r in bss))
print('no-bss list', sorted(r['overlay'] + ('' if r['dir'] == 'FLOW_PRG' else '(AT)') for r in nob))
neg = [(r['overlay'], r['bss_bytes']) for r in sl if int(r['bss_bytes']) < 0]
print('negative bss (_end before file end)', neg)
odd = [(r['overlay'], r['end_value'], r['end_rounded'], r['file_end']) for r in sl if int(r['end_rounded'], 16) - int(r['file_end'], 16) > 0x100000]
print('end_rounded far past file end (custom stub)', odd)
print('sum bss pad if every BSS overlay were padded', sum(int(r['bss_pad_cost'] or 0) for r in sl))
sl2 = [r for r in sl if r['append_cons'] != '']
cons = [int(r['append_cons']) for r in sl2]
print('append_cons min/median/max', min(cons), statistics.median(cons), max(cons), 'sum', sum(cons))
print('append_hard min/median/max', min(int(r['append_hard']) for r in sl2), statistics.median(int(r['append_hard']) for r in sl2), max(int(r['append_hard']) for r in sl2))
print('text ja bytes total (overlay rows)', sum(int(r['text_ja_bytes'] or 0) for r in rows if r['dir'] == 'FLOW_PRG'))
print('cons < 2 x text:', [(r['overlay'], r['dir'], r['append_cons'], r['text_ja_bytes']) for r in sl2 if r['append_cons_vs_text_x2'] == 'SHORT'])
print('cons < 64 KiB:', sorted((int(r['append_cons']), r['overlay'], r['dir']) for r in sl2 if int(r['append_cons']) < 65536))
print('measured overlays:')
for r in sl:
    if r['measured_in']:
        print('  %-13s %-8s heap %8s used %8s free %8s dirty_free %8s zero_run %8s img_match %5s%% tail_nz %5s bss_len %6s bss_nz %6s cons %8s  %s' % (
            r['overlay'], r['dir'], r['heap_bytes'], r['m_used'], r['m_free'], r['m_dirty_free'], r['m_zero_run'], r['m_img_match_pct'],
            r['m_tail_nz'], r['m_bss_len'], r['m_bss_nonzero'], r['append_cons'], r['measured_in']))

# ---- loader windows above the FONT slot
FB = 0x8CD5C000
f_root = os.path.getsize(os.path.join(ROOT, 'extracted', 'FONT.BIN'))
f_at = os.path.getsize(os.path.join(ROOT, 'extracted', 'ATFIRST', 'FONT.BIN'))
wins = [('FONT.BIN(root, loaded copy)', FB, f_root, 0x8CE02000), ('ATFIRST/FONT.BIN (not the loaded copy)', FB, f_at, 0x8CE02000)]
for nm, d in (('SHTEX0.ZAR', 0x8CE02000), ('BAR.TBD', 0x8CE2C000), ('SECFTEX0.ZAR', 0x8CE5C000)):
    wins.append((nm, d, os.path.getsize(os.path.join(ROOT, 'extracted', 'ATFIRST', nm)), None))
wins[2] = wins[2][:3] + (0x8CE2C000,)
wins[3] = wins[3][:3] + (0x8CE4C000,)          # BAR work pointers 0x8ce4c000/4 in 1ST_READ literals
wins[4] = wins[4][:3] + (0x8CE80000,)
print('boot-loaded resources (dest, size, end, next fixed address, spare):')
for nm, d, sz, nxt in wins:
    print('  %-40s dest %08x size %7d end %08x next %08x spare %7d (sector-rounded end %08x)' % (nm, d, sz, d + sz, nxt, nxt - d - sz, d + (sz + 2047) // 2048 * 2048))

# ---- slot table
print('slot table', [(hex(b), hex(s)) for b, s in m.slot_table()])

# ---- does the loader zero the sector tail / the BSS?  N_ENTRY (live1) vs the title dump (which had other data at the same addresses)
import gdrom  # noqa: E402
disc = gdrom.Disc(ROOT)
for nm, lba, size in (('N_ENTRY', 427423, 67320), ('HELP', 425352, 195381)):
    raw = disc.read(lba, (size + 2047) // 2048 * 2048)
    print('disc: %s sector tail after EOF %d bytes, non-zero %d' % (nm, len(raw) - size, len(raw) - size - raw[size:].count(0)))
t = m.load_dump('ram_2400')
l1 = m.load_dump('live1_ram')
NB = 0x8C8D0000
fe, se, ev = NB + 67320, NB + (67320 + 2047) // 2048 * 2048, 0x8C8E1654
a, b = l1[fe - m.BASE:se - m.BASE], t[fe - m.BASE:se - m.BASE]
print('N_ENTRY sector tail %08x..%08x len %d: non-zero in title dump %d, in live1 %d, identical %d' % (fe, se, len(a), len(b) - b.count(0), len(a) - a.count(0), sum(1 for x, y in zip(a, b) if x == y)))
a, b = l1[se - m.BASE:ev - m.BASE], t[se - m.BASE:ev - m.BASE]
print('N_ENTRY BSS beyond the last sector %08x..%08x len %d: non-zero in title dump %d, in live1 %d, byte-identical to title dump %d'
      % (se, ev, len(a), len(b) - b.count(0), len(a) - a.count(0), sum(1 for x, y in zip(a, b) if x == y)))

# ---- 1ST_READ.BIN tail overlapped by slot 0 / slot 1
f1 = m.r1st()
for lo, hi in ((0x8C2A0000, 0x8C2B0000), (0x8C2B0000, 0x8C2D0000), (0x8C2D0000, 0x8C2E0000)):
    seg = f1[lo - m.R1ST:hi - m.R1ST]
    same = sum(1 for dn in m.DUMPS if m.load_dump(dn)[lo - m.BASE:hi - m.BASE] == seg)
    print('1ST_READ tail %08x..%08x: file nonzero bytes %d of %d; dumps (of 4) where RAM == file: %d'
          % (lo, hi, len(seg) - seg.count(0), len(seg), same))
print('1ST_READ.BIN size', len(f1), 'end', hex(m.R1ST + len(f1)))

# ---- stack
top = len(t)
while top and t[top - 1] == 0:
    top -= 1
print('highest non-zero RAM byte in title dump', hex(m.BASE + top - 1), ' last 16 bytes', t[-16:].hex())

# ---- biggest text holders vs append budget
print('top 20 overlays by JA text bytes (sum of max_bytes): name, text, records, has_bss, bss_pad, append_cons, append_hard, heap')
tt = sorted(((int(r['text_ja_bytes']), r) for r in rows if r['text_ja_bytes'] and r['dir'] == 'FLOW_PRG'), key=lambda t: -t[0])
for tb, r in tt[:20]:
    print('  %-13s text %8d recs %5s bss %7s pad %8s cons %8s hard %8s heap %8s %s' % (
        r['overlay'], tb, r['text_records'], r['has_bss'], r['bss_pad_cost'], r['append_cons'], r['append_hard'], r['heap_bytes'], r['note'][:50]))
print('overlays whose text exceeds append_cons:', [(r['overlay'], r['text_ja_bytes'], r['append_cons']) for r in rows
                                                  if r['text_ja_bytes'] and r['append_cons'] != '' and int(r['text_ja_bytes']) > int(r['append_cons']) and r['dir'] == 'FLOW_PRG'])
ntext = sum(int(r['text_ja_bytes']) for r in rows if r['text_ja_bytes'] and r['dir'] == 'FLOW_PRG')
print('total JA text bytes in FLOW_PRG overlays', ntext, ' sum append_cons over FLOW_PRG overlays', sum(int(r['append_cons']) for r in rows if r['append_cons'] != '' and r['dir'] == 'FLOW_PRG'))
