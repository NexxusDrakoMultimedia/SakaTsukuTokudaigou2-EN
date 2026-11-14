"""art1_tdbfix - private copy of translation/ for the trial build with the two orphan records that fall inside compressed
texture streams blanked (en = '' means keep the original).  python -I -X utf8 tools/re/art1_tdbfix.py"""
import os, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'build', 'art1', 'tdb')
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
BAD = {'FLOW_PRG/LOADBAR.BIN#7330', 'FLOW_PRG/YOUTH.BIN#422ee'}
n = 0
for fn in os.listdir(os.path.join(ROOT, 'translation')):
    p = os.path.join(ROOT, 'translation', fn)
    if not os.path.isfile(p): continue
    if not fn.endswith('.jsonl'):
        shutil.copy(p, OUT); continue
    out = []
    for line in open(p, encoding='utf8'):
        if line.strip():
            r = json.loads(line)
            if r.get('id') in BAD:
                r['en'] = ''; n += 1
                line = json.dumps(r, ensure_ascii=False) + '\n'
        out.append(line)
    open(os.path.join(OUT, fn), 'w', encoding='utf8', newline='').write(''.join(out))
print('blanked', n)
