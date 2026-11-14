"""tx5: list the name-folder segments tx5_names.py could not resolve (distinct ja, with the clip stems).  Writes build/tx5/names_left.tsv."""
import os, sys, json, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
done = {}
p = os.path.join(ROOT, 'build', 'tx5', 'results', 'names.tsv')
for ln in open(p, encoding='utf8'):
    k, _, v = ln.rstrip('\n').partition('\t')
    done[k] = v
left = collections.OrderedDict()
for ln in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8'):
    r = json.loads(ln)
    if r['ctx'].startswith('clip name') and r['id'] not in done and not r.get('en'):
        left.setdefault(r['ja'], []).append(r['ctx'].split()[1].split('\\')[1])
with open(os.path.join(ROOT, 'build', 'tx5', 'names_left.tsv'), 'w', encoding='utf8', newline='\n') as f:
    for i, (ja, st) in enumerate(left.items()):
        f.write('%d\t%s\t%s\n' % (i, ja, ' '.join(sorted(set(st))[:3])))
print(len(left))
for i, (ja, st) in enumerate(left.items()):
    print(i, ja, st[0])
