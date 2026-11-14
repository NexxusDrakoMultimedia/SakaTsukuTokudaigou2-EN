"""tx5: list ja-only records that contain Japanese for a set of sources (regex on the source id).
python -I -X utf8 tools/re/tx5_list_left.py REGEX [--skip]      e.g. 'FLOW_PRG/(GAME|BPMATCH)\\.BIN'   (--skip also shows the skip flag)"""
import glob, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
JP = re.compile(r'[぀-ヿ一-鿿ｦ-ﾟ]')
rx = re.compile(sys.argv[1])
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    if 'BCAST' in p:
        continue
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        src = r['id'].rsplit('#', 1)[0]
        if rx.search(src) and not r.get('en') and JP.search(r['ja']):
            print('%s\t%s\t%s\t%s' % (r['id'], r.get('max_bytes'), 'SKIP' if r.get('skip') else '', json.dumps(r['ja'], ensure_ascii=False)))
