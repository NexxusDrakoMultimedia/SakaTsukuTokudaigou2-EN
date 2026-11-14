import json, sys
g = json.load(open('build/art/groups.json', encoding='utf8'))
want = sys.argv[1:]
def walk(x):
    if isinstance(x, dict):
        if 'ids' in x:
            yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)
for grp in walk(g):
    hit = [w for w in want if w in grp['ids']]
    print(grp.get('name'), hit)
