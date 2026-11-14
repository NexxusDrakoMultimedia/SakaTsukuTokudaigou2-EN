"""tx5: list the hw katakana tokens of the tm_/stadi clip lines whose lexicon English looks abbreviated (for manual full forms)."""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))
import tx5_mech as M
lex = M.lexicon()
toks = set()
for ln in open(os.path.join(ROOT, 'build', 'tx5', 'distinct.tsv'), encoding='utf8'):
    p = ln.rstrip('\n').split('\t')
    if not any(re.match(r'yh_(tm_|stadi)', s) for s in p[4].split()):
        continue
    for m in re.finditer(M.HW, p[2]):
        t = m.group(0)
        for suf in ('ｽﾀｼﾞｱﾑ',):
            if t.endswith(suf) and len(t) > len(suf):
                t = t[:-len(suf)]
        toks.add(t)
out = []
for t in sorted(toks):
    e = lex.get(t)
    if e is None:
        out.append((t, '???'))
    elif '.' in e or len(e) <= 3 or e.isupper() or re.search(r'[a-z][A-Z]', e):
        out.append((t, e))
print(len(toks), 'tokens', len(out), 'suspicious')
for t, e in out:
    print('%s\t%s' % (t, e))
