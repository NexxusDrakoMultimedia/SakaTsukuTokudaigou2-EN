"""skp (skeptic): en strings with a run of 2+ blanks followed by a glyph (the case the blank-run snap changes); read-only."""
import glob, json, os, re, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'translation')
n = 0
for f in sorted(glob.glob(os.path.join(root, '*.jsonl'))):
    for line in open(f, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get('en')
        if not en:
            continue
        for ln in en.split('\n'):
            m = re.search(r'\S(  +)\S', ln)
            if m:
                n += 1
                print(os.path.basename(f)[:-6], r['id'].split('#')[-1], repr(ln)[:90])
                break
print('total', n)
