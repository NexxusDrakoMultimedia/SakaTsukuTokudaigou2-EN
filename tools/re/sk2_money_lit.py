import glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pat = re.compile(r'(\bY ?[0-9][0-9.,]*\s?(bn|M|K|m|k)?\b|million|billion|\bbn\b|thousand yen|\byen\b|\d+\s?(Oku|Man)\b|\bOku\b|\bMan\b)')
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for line in open(p, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        en = r.get('en') or ''
        if pat.search(en):
            print(r['id'], '|', en.replace('\n', ' / ')[:160], '|| JA:', (r.get('ja') or r.get('jp') or '').replace('\n', ' / ')[:70])
