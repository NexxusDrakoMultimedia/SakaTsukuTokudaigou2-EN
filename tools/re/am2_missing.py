"""am2_missing - ids of groups 1-7 with no repainted file in translation/textures."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art7_lib as L
g = json.load(open(os.path.join(L.ROOT, 'build', 'art', 'groups.json')))['groups']
for gi, grp in enumerate(g, 1):
    miss = []
    for i in grp['ids']:
        try:
            src, tid, d = L.resolve(i)
        except KeyError:
            miss.append(i + '?'); continue
        p = os.path.join(L.TEXDIR, *src.split('/'), tid + '.pvr')
        if not os.path.exists(p):
            miss.append('%s(%s %s)' % (i, src, tid))
    print(gi, len(grp['ids']), 'missing:', miss)
