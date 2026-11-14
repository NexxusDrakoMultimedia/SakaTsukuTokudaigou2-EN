"""dsc_plantry: plan-only experiments for the disc planner (no tracks written).  python -I -X utf8 tools/re/dsc_plantry.py"""
import os, sys, struct, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D

src = D.Source('.')
t = time.time()
pl = D.plan_patches(src, {})
print('noop over', len(pl.over), 'end', pl.new_end, '%.1fs' % (time.time() - t))
pvd, rl, rs, recs = D.read_filesystem(src)
dirs = {'/': rl}
for r in recs:
    if r.isdir:
        dirs[r.path.upper()] = r.lba
pts, = struct.unpack_from('<I', pvd, 132)
for off, e in ((140, '<'), (148, '>')):
    pl_, = struct.unpack_from(e + 'I', pvd, off)
    orig = src.read(pl_, pts)
    mine = D.path_table(dirs, e)
    print('PT', e, 'regen equal', orig == mine, len(orig), len(mine))
t = time.time()
pl = D.plan_patches(src, {}, dedupe=True)
print('dedupe: groups', len(pl.dedupe), 'followers', sum(len(g[1]) for g in pl.dedupe), 'over', len(pl.over),
      'free', pl.free_sectors, '%.1fs' % (time.time() - t))
print('dir sectors rewritten', sorted(pl.over))
pl = D.plan_patches(src, {}, add_files={'/README.TXT': b'hello', '/EN/NOTE.TXT': b'x' * 5000}, add_dirs=['/EN2'])
print('add: over', len(pl.over), 'added', pl.added, 'newdirs', pl.new_dirs, 'moved', pl.moved_dirs)
print(sorted(pl.over))
