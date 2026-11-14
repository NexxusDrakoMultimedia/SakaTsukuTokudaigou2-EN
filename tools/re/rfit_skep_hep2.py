"""skeptic: flag odd Hepburn outputs"""
import glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
seen = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
    for ln in open(f, encoding='utf-8'):
        if ln.strip():
            r = json.loads(ln)
            if r['cls'] == 'person' and r['why'].startswith('Hepburn'):
                seen[(r['ja'], r['en'])] = 1
pats = {'oo': r'oo|uu|ou\b|oh', 'tu/si/hu/zi/ti': r'tu|si|hu|zi|ti(?!a)|sya|tya', 'nb/nm/np': r'n[bmp]', 'wo': r'wo', 'double-vowel-end': r'[aeiou]{3}', 'dzu': r'du|dzu', 'xx': r'[^aeiou]{4}'}
for k, p in pats.items():
    hits = [(j, e) for (j, e) in seen if re.search(p, e.lower())]
    print(k, len(hits), hits[:25])
print('total', len(seen))
# lengths of ja vs en: ratio
import collections
c = collections.Counter(len(e) for j, e in seen)
print(sorted(c.items()))
