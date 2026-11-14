"""List records whose Japanese is a picker-style grid (only full-width letters/digits/kana/spaces/newlines, >= 3 lines or >= 20 chars,
no punctuation sentence) and that still carry English or lack skip.   python -I -X utf8 tools/re/find_grids.py"""
import glob, json, os, re
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GRID = re.compile(r'^[\s　０-９Ａ-Ｚａ-ｚぁ-んァ-ヴー]+$')
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    with open(f, encoding='utf8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            ja = r['ja']
            if ('\n' in ja or len(ja) >= 20) and GRID.match(ja) and len(ja.strip()) >= 8:
                print('%s skip=%s en=%r  %r' % (r['id'], bool(r.get('skip')), (r.get('en') or '')[:20], ja[:30]))
