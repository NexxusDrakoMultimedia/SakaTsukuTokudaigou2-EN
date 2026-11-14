"""hng: compare the control markers of ja and en of every record: leading '=x/' and trailing '=' frames, '$N' arguments, '@X/' ... '@' spans, <..> tokens.
usage: hng_markers.py [SOURCE-substring]"""
import glob, json, os, re, sys
from collections import Counter
src = sys.argv[1] if len(sys.argv) > 1 else ''
LEAD = re.compile(r'^(=\w/)')
bad = Counter(); n = 0
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        ja, en = r['ja'], r.get('en') or ''
        if not en or r.get('skip'):
            continue
        n += 1
        probs = []
        la, lb = LEAD.match(ja), LEAD.match(en)
        if (la.group(1) if la else None) != (lb.group(1) if lb else None):
            probs.append('lead %r vs %r' % (la and la.group(1), lb and lb.group(1)))
        if ja.endswith('=') != en.endswith('='):
            probs.append('trail= %s vs %s' % (ja.endswith('='), en.endswith('=')))
        if Counter(re.findall(r'\$\d', ja)) != Counter(re.findall(r'\$\d', en)):
            probs.append('$N %s vs %s' % (re.findall(r'\$\d', ja), re.findall(r'\$\d', en)))
        sa = Counter(re.findall(r'@[A-Za-z]/', ja)); sb = Counter(re.findall(r'@[A-Za-z]/', en))
        if sa != sb:
            probs.append('@X/ %s vs %s' % (dict(sa), dict(sb)))
        if ja.count('@') != en.count('@'):
            probs.append('@ count %d vs %d' % (ja.count('@'), en.count('@')))
        if re.findall(r'<[^>]*>', ja) != re.findall(r'<[^>]*>', en):
            probs.append('<..> %s vs %s' % (re.findall(r'<[^>]*>', ja), re.findall(r'<[^>]*>', en)))
        if probs:
            bad[os.path.basename(p)] += 1
            if bad[os.path.basename(p)] <= 4:
                print(r['id'], probs, repr(en[:60]))
print('checked', n, 'with differing markers', sum(bad.values()))
for k, v in bad.most_common(12):
    print('  %-40s %d' % (k, v))
