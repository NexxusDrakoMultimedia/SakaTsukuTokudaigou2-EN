"""Write build/trans/todo/NNNN.json for every shard that still has untranslated items.
   python -I -X utf8 tools/re/pending_keys.py        -> {"shard": N, "keys": [...], "done": [...]}
A text is untranslated when NONE of its records has a non-empty en and the shard item has no skip hint.
Prints one line per shard: shard, todo, total."""
import glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(root, 'tools'))
import translib

has_en = set()
for f in glob.glob(os.path.join(root, 'translation', '*.jsonl')):
    with open(f, encoding='utf8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if (r.get('en') or '').strip() or r.get('skip'):
                    has_en.add(translib.key_of(r['ja']))
out = os.path.join(root, 'build', 'trans', 'todo')
os.makedirs(out, exist_ok=True)
for old in glob.glob(os.path.join(out, '*.json')):
    os.remove(old)
n_shards = n_items = 0
for f in sorted(glob.glob(os.path.join(root, 'build', 'trans', 'shards', '*.json'))):
    with open(f, encoding='utf8') as fh:
        sh = json.load(fh)
    todo = [it['key'] for it in sh['items'] if not it.get('skip') and it['key'] not in has_en]
    if not todo:
        continue
    done = [it['key'] for it in sh['items'] if it['key'] in has_en]
    with open(os.path.join(out, '%04d.json' % sh['shard']), 'w', encoding='utf8') as fh:
        json.dump({'shard': sh['shard'], 'keys': todo, 'done': done}, fh)
    print('%d\t%d\t%d' % (sh['shard'], len(todo), len(sh['items'])))
    n_shards += 1
    n_items += len(todo)
print('%d shards, %d items to do' % (n_shards, n_items), file=sys.stderr)
