"""Read-only what-if planner: free space under several reclamation policies and the placement of a hypothetical growth.
No disc is written.  usage: dxp_plan.py [growth_percent_for_FLOW_PRG_overlays]"""
import os, sys, hashlib, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
pct = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
files = [r for r in recs if not r.isdir and r.size]
ext = D.used_extents(src, pvd, rl, rs, recs)
gaps = D.free_gaps(ext, src.end_lba)
base_free = sum(g[1] for g in gaps)
print('A  zero gaps (track3 tail 6281 + end 150):', base_free, 'sectors =', base_free * 2048, 'bytes; largest contiguous', max(g[1] for g in gaps))
# B duplicates
by = collections.defaultdict(list)
for r in files:
    by[(r.size, hashlib.sha1(src.read(r.lba, r.size)).hexdigest())].append(r)
freed_b = []
for k, g in by.items():
    for r in sorted(g, key=lambda r: r.path)[1:]:
        freed_b.append((r.lba, D._nsec(r.size), r.path))
sb = sum(n for _, n, _ in freed_b)
print('B  + shared extents for byte-identical files:', sb, 'sectors', sb * 2048, 'bytes; %d extents, largest %d' % (len(freed_b), max(n for _, n, _ in freed_b)))
# C DP browser tree
dp = [r for r in files if r.path.split('/')[1].startswith('DP') or r.path in ('/2_DP.BIN', '/DP3.INI', '/MANATEE.DRV', '/NAMIHEI.DRV', '/MAIGO.BIN', '/SG_DPLDR.BIN')]
sc = sum(D._nsec(r.size) - 1 for r in dp)
print('C  + Dream Passport browser tree emptied to 1-sector stubs (%d files):' % len(dp), sc, 'sectors', sc * 2048, 'bytes')
for r in sorted(dp, key=lambda r: -r.size)[:6]: print('      %9d %s' % (r.size, r.path))
# D CDDA track 4
print('D  + audio track 4 reclaimed (needs a layout shift of track 5 start, content decision):', 5323 - 300, 'sectors (keep 150 pregap + 150 min)')
tot = base_free + sb + sc
print('A+B+C = %d sectors = %.1f MB;  +D = %.1f MB' % (tot, tot * 2048 / 1e6, (tot + 5023) * 2048 / 1e6))
# growth scenario
ov = [r for r in files if r.path.startswith('/FLOW_PRG/') and r.path.endswith('.BIN')]
need = []
for r in ov:
    n_old = D._nsec(r.size); n_new = D._nsec(int(r.size * (1 + pct / 100)))
    if n_new > n_old: need.append((r.path, n_old, n_new))
moved_new = sum(n for _, _, n in need); freed_old = sum(o for _, o, _ in need)
print('growth %.1f%% of %d overlays: %d files cross a sector boundary, new extents %d sectors (%.1f MB), vacated %d sectors' % (pct, len(ov), len(need), moved_new, moved_new * 2048 / 1e6, freed_old))
print('   net extra sectors needed:', moved_new - freed_old, ' available (A only):', base_free)
print('   cost if the delta is positional (files stored whole): %.1f MB; if the encoder is move-aware: ~ size of edited text' % (moved_new * 2048 / 1e6))
# all-FLOW_PRG-overlay total
print('all 114 FLOW_PRG overlays together:', sum(D._nsec(r.size) for r in ov), 'sectors', sum(r.size for r in ov) / 1e6, 'MB')
