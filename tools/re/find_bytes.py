"""Find where Japanese strings live in the original disc files (extracted/), as cp932 bytes, and say whether the translation DB has
a record at that offset.   python -I -X utf8 tools/re/find_bytes.py 'は　い' 'いいえ' ...   [--root extracted]
Prints  file  offset(hex)  string, and 'DB:<id>' when a record id ends with that offset."""
import glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
base = os.path.join(root, 'extracted')
if '--root' in sys.argv:
    base = os.path.join(root, sys.argv[sys.argv.index('--root') + 1])
    args = [a for a in args if a != sys.argv[sys.argv.index('--root') + 1]]
ids = set()
for f in glob.glob(os.path.join(root, 'translation', '*.jsonl')):
    with open(f, encoding='utf8') as fh:
        for ln in fh:
            if ln.strip():
                ids.add(json.loads(ln)['id'])
for s in args:
    pat = s.encode('cp932')
    print('==', s, pat.hex())
    for dp, dn, fn in os.walk(base):
        for name in fn:
            p = os.path.join(dp, name)
            try:
                data = open(p, 'rb').read()
            except OSError:
                continue
            i = data.find(pat)
            n = 0
            while i >= 0 and n < 6:
                rel = os.path.relpath(p, base).replace('\\', '/')
                hit = [x for x in ids if x.startswith(rel.rsplit('.', 0)[0] + '#') and x.endswith('#%x' % i)]
                print('  %s +0x%x %s' % (rel, i, ('DB:' + hit[0]) if hit else 'no record'))
                n += 1
                i = data.find(pat, i + 1)
