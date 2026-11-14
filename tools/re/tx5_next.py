"""tx5: print the next untranslated distinct lines (frozen numbering of build/tx5/distinct.tsv), skipping the ones a results file
already covers.   python -I -X utf8 tools/re/tx5_next.py [COUNT=250] [START_N]"""
import glob, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TX = os.path.join(ROOT, 'build', 'tx5')
count = int(sys.argv[1]) if len(sys.argv) > 1 else 250
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
have = set()
for ln in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8'):
    r = json.loads(ln)
    if r.get('en'):
        have.add(r['ja'])
done = set()
for fp in glob.glob(os.path.join(TX, 'results', '*.tsv')):
    b = os.path.basename(fp)
    if b.startswith('names'):
        continue
    for ln in open(fp, encoding='utf8'):
        k = ln.split('\t', 1)[0]
        if k.isdigit():
            done.add(int(k))
n = 0
for ln in open(os.path.join(TX, 'distinct.tsv'), encoding='utf8'):
    p = ln.rstrip('\n').split('\t')
    i = int(p[0])
    if i < start or i in done or p[2] in have:
        continue
    if len(sys.argv) > 3 and not any(s.startswith(sys.argv[3] + '_') for s in p[4].split()):
        continue
    print('%d\t%s' % (i, p[2]))
    n += 1
    if n >= count:
        break
