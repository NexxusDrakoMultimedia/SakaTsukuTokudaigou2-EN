"""Independent recount of the pool agent's population / capacity headline numbers (agent synth)."""
import sys, os, importlib.util, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
os.chdir(ROOT); sys.path.insert(0, 'tools')
import textrepack as R
spec = importlib.util.spec_from_file_location('pc', 'tools/re/capacity/pool/common.py'); pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
imgs = pc.load_all('full')
n = mov = fix = pools = cap = jpmov = jpfix = single = 0
orph = pin = inter = 0
fixmax = 0
for src, img, strs, ptrs in imgs:
    n += len(strs)
    ps, where = R.find_pools(strs)
    pools += len(ps); cap += sum(p.cap for p in ps); single += sum(1 for p in ps if len(p.home) == 1)
    for s in strs:
        if R.is_movable(s): mov += 1; jpmov += len(s.raw) + 1
        else:
            fix += 1; jpfix += len(s.raw) + 1
            orph += bool(s.orphan); pin += bool(s.pinned); inter += bool(s.interior)
print('images', len(imgs), 'strings', n, 'movable', mov, 'fixed', fix, '(orphan %d pinned %d interior %d flags)' % (orph, pin, inter))
print('pools', pools, 'single-string pools', single, 'pool capacity', cap, 'movable JP bytes', jpmov, 'slack', cap - jpmov, '%.2f%%' % (100.0 * (cap - jpmov) / jpmov))
print('fixed JP bytes', jpfix)
