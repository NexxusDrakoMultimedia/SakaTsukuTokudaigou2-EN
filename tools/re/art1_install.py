"""art1_install - copy the repainted group-1 PVRs to every identical copy.
python -I -X utf8 tools/re/art1_install.py [--final]   (always writes build/art1/texdir; --final also translation/textures)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
B = os.path.join(ROOT, 'build', 'art1')
man = json.load(open(os.path.join(B, 'manifest.json')))
dests = [os.path.join(B, 'texdir')] + ([os.path.join(ROOT, 'translation', 'textures')] if '--final' in sys.argv else [])
n = 0
HELD = set()   # am2: LOADBAR 07332 and YOUTH.BIN 10469 were held because of two orphan text records; their en is now blank so they install normally
for i, m in man.items():
    data = open(os.path.join(B, 'new', i + '.pvr'), 'rb').read()
    for f, tid in m['copies']:
        for d in dests:
            if i in HELD and d != dests[0]:
                d = os.path.join(B, 'held')
            p = os.path.join(d, *f.split('/'), tid + '.pvr')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(data)
        n += 1
print('wrote', n, 'files to', dests)
