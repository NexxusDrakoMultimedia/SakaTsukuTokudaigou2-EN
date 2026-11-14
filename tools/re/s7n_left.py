"""s7n: records whose en still carries an old (non-art) form.  usage: s7n_left.py out.tsv"""
import json, glob, os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLD = re.compile(r"\b(Reds|Belmare|Sanfrec|Consado|Montedo|Frontal|Holyhok|HollyHock|FCTokyo|FC Tokyo|Yoko\.FC|AllEast|AllWest|All East|All West|PurpleSanga|"
                 r"World XI|European XI|Euro XI|Japan Stars|Asia Stars|Africa Stars|Nordic Stars|Spain Legends|France Legends|U\.K\. Legends|Netherlands Legends|"
                 r"Argentina Legends|Italy Legends|Germany Legends|Brazil Legends|Europe Super|South America Super|Europe Old|South America Old|"
                 r"Fan Appreciation|Fan Thanks|Thank-You Match|Asian Winners|Asian Challenge Cup|Asian Tournament|European Cup|European Challenge League|"
                 r"South American Challenge|South American Cup|Pre-[Ss]eason|World Sports Games|World Games|Champ Cup|JEF|Vissel|Sagan|Marinos|Dream Club)\b")
rows = []
cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        en = r.get('en') or ''
        ms = sorted(set(m.group(1) for m in OLD.finditer(en)))
        if ms:
            ctx = r.get('ctx') or ''
            kind = 'hwpool' if 'hwpool' in ctx else (r.get('fmt') or 'ptr')
            for m in ms:
                cnt[(m, kind)] += 1
            rows.append('\t'.join([','.join(ms), kind, r['id'], str(r.get('max_bytes')), r['ja'].replace('\n', '\n')[:70], en.replace('\n', '\n')[:110]]))
open(sys.argv[1], 'w', encoding='utf8').write('\n'.join(sorted(rows)) + '\n')
for k, v in sorted(cnt.items()):
    print(k, v)
