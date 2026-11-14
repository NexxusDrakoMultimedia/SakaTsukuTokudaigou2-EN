"""List translation records that look like character-picker grids (data tables, not prose): several lines of equal
length made only of kana / full-width alphanumerics / punctuation / spaces.  Output: tab-separated id, rows, width,
first line, current en first line.   python -I -X utf8 tools/re/find_grid_tables.py [--clear]
--clear sets en to '' for the listed records (atomic rewrite of each jsonl, preserves every other field/line)."""
import glob, json, os, re, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CELL = re.compile(r'^[ぁ-ゖァ-ー０-９Ａ-Ｚａ-ｚ　 ー・！？＆，．、。＜＞（）［］｛｝＋＊／：－\'’]+$')


def is_grid(ja):
    lines = ja.split('\n')
    if len(lines) < 3:
        return False
    if not all(CELL.match(l) for l in lines if l):
        return False
    widths = [len(l.rstrip('　 ')) for l in lines]
    return max(widths) >= 8 and max(widths) - min(widths) <= 4


hits = []
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    with open(f, encoding='utf8') as fh:
        for n, line in enumerate(fh):
            if not line.strip():
                continue
            r = json.loads(line)
            if is_grid(r['ja']):
                hits.append((f, n, r))
for f, n, r in hits:
    print('%s\t%d\t%d\t%s\t%s' % (r['id'], r['ja'].count('\n') + 1, len(r['ja'].split('\n')[0]),
                                  r['ja'].split('\n')[0].replace('　', '_'), (r.get('en') or '').split('\n')[0]))
print('%d grid-like records' % len(hits), file=sys.stderr)
if '--clear' in sys.argv:
    byfile = {}
    for f, n, r in hits:
        byfile.setdefault(f, set()).add(n)
    for f, ns in byfile.items():
        with open(f, encoding='utf8', newline='') as fh:
            lines = fh.read().split('\n')
        for n in ns:
            r = json.loads(lines[n])
            r['en'] = ''
            lines[n] = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write('\n'.join(lines))
        os.replace(tmp, f)
    print('cleared en of %d records in %d files' % (len(hits), len(byfile)), file=sys.stderr)
