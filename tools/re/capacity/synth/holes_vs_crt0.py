"""Cross-check memmap's 'clean 1ST_READ zero holes' (build/memmap/holes.tsv, 557,056 B) against the crt0 zero-fill ranges
found by the bank agent (docs/trans-bank.md s2.2: words [0x8c16f800,0x8c299400), bytes [0x8c193c30,0x8c1fc180)).
Bytes stored in a cleared range are destroyed before main, so they cannot hold a bank.
  python -I -X utf8 tools/re/capacity/synth/holes_vs_crt0.py"""
import csv, os
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
clear = [(0x8c16f800, 0x8c299400), (0x8c193c30, 0x8c1fc180)]
tot = keep = 0
for r in csv.DictReader(open(os.path.join(root, 'build', 'memmap', 'holes.tsv')), delimiter='\t'):
    a, z = int(r['start'], 16), int(r['end'], 16)
    # union of clear ranges
    u = [(0x8c16f800, 0x8c299400)]       # the second range is inside the first
    cleared = max(0, min(z, u[0][1]) - max(a, u[0][0]))
    tot += z - a; keep += (z - a) - cleared
    print('%s-%s %7d B: %7d B inside crt0 BSS clear, %7d B survive' % (r['start'], r['end'], z - a, cleared, z - a - cleared))
print('memmap holes %d B; surviving (not zero-filled by crt0) %d B; cleared %d B (%.1f %%)' % (tot, keep, tot - keep, 100.0 * (tot - keep) / tot))
