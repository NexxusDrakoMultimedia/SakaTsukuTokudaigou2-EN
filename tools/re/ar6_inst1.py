"""ar6_inst1: install selected art1 results into translation/textures (every identical copy): ar6_inst1.py ID ..."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
B = os.path.join(ROOT, 'build', 'art1')
man = json.load(open(os.path.join(B, 'manifest.json')))
for i in sys.argv[1:]:
    data = open(os.path.join(B, 'new', i + '.pvr'), 'rb').read()
    for f, tid in man[i]['copies']:
        p = os.path.join(ROOT, 'translation', 'textures', *f.split('/'), tid + '.pvr')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        print(i, p)
