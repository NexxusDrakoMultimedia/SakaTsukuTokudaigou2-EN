"""tx5 skeptic: for every record with English compare the control markup of ja and en: leading '=x/' selector, trailing '=', the @X/ ... @ opens and
closes, #tok# tokens, %-specs, <XX> byte tokens.  Prints the mismatches (a missing '=' or '@' can leave the message window empty or stuck)."""
import json, glob, re, collections, sys
rx=re.compile(r'^=[A-Za-z]/|=$|@[A-Z]/|@|#[A-Za-z0-9_]+#|%[-+ #0]*\d*(?:\.\d+)?[a-zA-Z]|<[0-9A-F]{2}>')
bad=collections.defaultdict(list); n=0
for f in sorted(glob.glob('translation/*.jsonl')):
    if 'BCAST' in f: continue
    for l in open(f,encoding='utf8'):
        r=json.loads(l)
        if not r.get('en') or r.get('skip'): continue
        n+=1
        a=collections.Counter(rx.findall(r['ja'])); b=collections.Counter(rx.findall(r['en']))
        if a!=b:
            bad[f.split('/')[-1].replace('.jsonl','')].append((r['id'].split('#')[1],dict(a-b),dict(b-a),r['ja'][:30].replace('\n','/'),r['en'][:40].replace('\n','/')))
print('checked',n,'mismatching',sum(len(v) for v in bad.values()))
for k,v in sorted(bad.items(),key=lambda x:-len(x[1]))[:25]:
    print(k,len(v)); 
    for x in v[:3]: print('    ',x)
