"""s7n: byte length (with NUL) of a record's en as the build encodes it.  usage: s7n_bytes.py ID"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_common as C
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    src = p
    for ln in open(p, encoding='utf8'):
        if sys.argv[1] in ln[:200]:
            r = json.loads(ln)
            if r['id'] == sys.argv[1]:
                print(len(C.encode_text(r['en'])) + 1, r.get('max_bytes'), repr(r['en']), r.get('ctx'))
