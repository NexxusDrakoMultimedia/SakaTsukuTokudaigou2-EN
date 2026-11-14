"""Read-only: exact duplicate files on the disc (sha1) and the sectors a shared extent would save. usage: dxp_dups.py"""
import os, sys, hashlib, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
src = D.Source('.')
pvd, rl, rs, recs = D.read_filesystem(src)
files = [r for r in recs if not r.isdir and r.size]
by = collections.defaultdict(list)
for r in files:
    by[(r.size, hashlib.sha1(src.read(r.lba, r.size)).hexdigest())].append(r)
save = 0; nd = 0
for (sz, h), rs_ in sorted(by.items(), key=lambda kv: -kv[0][0] * (len(kv[1]) - 1)):
    if len(rs_) > 1:
        s = D._nsec(sz) * (len(rs_) - 1)
        save += s; nd += 1
        if sz >= 8192 or len(rs_) > 2:
            print('%9d x%d  %s' % (sz, len(rs_), ' '.join(r.path for r in rs_)))
print('duplicate groups', nd, 'sectors saved by extent sharing', save, 'bytes', save * 2048)
# lba shared already?
c = collections.Counter(r.lba for r in files)
print('files already sharing an extent', sum(1 for v in c.values() if v > 1))
