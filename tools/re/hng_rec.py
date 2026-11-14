"""hng: print one record from the current DB and from an older snapshot dir.  usage: hng_rec.py SOURCEFILE ID [OLD_DIR]"""
import json, os, sys
fn, rid = sys.argv[1], sys.argv[2]
dirs = ['translation'] + sys.argv[3:]
for d in dirs:
    for ln in open(os.path.join(d, fn), encoding='utf-8'):
        if rid in ln:
            r = json.loads(ln)
            if r['id'] == rid:
                print('==', d); print('ja:', repr(r['ja'])); print('en:', repr(r.get('en'))); print({k: v for k, v in r.items() if k not in ('ja', 'en', 'id')})
