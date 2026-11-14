"""Split build/trans/propagate_unfit.tsv into build/trans/slotfit/in_NN.tsv chunks of distinct (ja, slot, known forms)
   so agents can write build/trans/slotfit/out_NN.tsv.  python -I -X utf8 tools/re/split_unfit.py [CHUNK=110]"""
import os, sys, ast
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
chunk = int(sys.argv[1]) if len(sys.argv) > 1 else 110
rows = {}
with open(os.path.join(root, 'build', 'trans', 'propagate_unfit.tsv'), encoding='utf8') as fh:
    for line in fh:
        rid, ja, slot, forms = line.rstrip('\n').split('\t')
        rows[(int(slot), ja)] = ast.literal_eval(forms)
keys = sorted(rows)
out = os.path.join(root, 'build', 'trans', 'slotfit')
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    os.remove(os.path.join(out, f))
n = 0
for i in range(0, len(keys), chunk):
    n += 1
    with open(os.path.join(out, 'in_%02d.tsv' % n), 'w', encoding='utf8') as fh:
        for slot, ja in keys[i:i + chunk]:
            fh.write('%s\t%d\t%s\n' % (ja, slot, ' | '.join(rows[(slot, ja)])))
print(n, 'chunks,', len(keys), 'items')
