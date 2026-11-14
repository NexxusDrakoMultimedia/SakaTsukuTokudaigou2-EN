"""hng: show the English of given record ids in every snapshot of the translation DB found under build/ (and translation/), with file mtimes.
usage: hng_hist.py SOURCE-file-name ID [ID ...]    e.g. hng_hist.py FLOW_PRG__EVENT.BIN.jsonl FLOW_PRG/EVENT.BIN#15043b"""
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fn, ids = sys.argv[1], set(sys.argv[2:])
paths = []
for dp, dn, fns in os.walk(os.path.join(ROOT, 'build')):
    dn[:] = [d for d in dn if d not in ('trial', 'out', 'emu')]
    if fn in fns:
        paths.append(os.path.join(dp, fn))
paths.append(os.path.join(ROOT, 'translation', fn))
for p in sorted(paths, key=os.path.getmtime):
    got = {}
    for ln in open(p, encoding='utf-8'):
        if any(i in ln for i in ids):
            r = json.loads(ln)
            if r['id'] in ids:
                got[r['id']] = r.get('en')
    print(time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p))), os.path.relpath(p, ROOT), {k.split('#')[1]: v for k, v in got.items()})
