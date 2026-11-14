"""Set en to '' (keep the Japanese original) for the given record ids, with an atomic rewrite of each jsonl.
   python -I -X utf8 tools/re/clear_en_ids.py ID [ID ...]     (also adds "skip": true so the planner and merge tools
   never hand the record to a translator again; prints what changed)"""
import glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
want = set(sys.argv[1:])
done = set()
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    with open(f, encoding='utf8', newline='') as fh:
        lines = fh.read().split('\n')
    changed = False
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        r = json.loads(line)
        if r['id'] in want:
            print('%s: en %r -> ""' % (r['id'], (r.get('en') or '')[:40]))
            r['en'] = ''
            r['skip'] = True
            lines[i] = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
            done.add(r['id'])
            changed = True
    if changed:
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write('\n'.join(lines))
        os.replace(tmp, f)
missing = want - done
if missing:
    print('not found:', ', '.join(sorted(missing)))
    sys.exit(1)
