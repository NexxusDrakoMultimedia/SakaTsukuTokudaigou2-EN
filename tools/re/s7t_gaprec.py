"""s7t: add the SCHE0/SCHE1 stadium-suffix gap record (extract + en) into translation/*.jsonl by id, atomically."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_gap as G
EN = {'FLOW_PRG/SCHE0.BIN': '%s Stadium', 'FLOW_PRG/SCHE1.BIN': '%s Stadium'}
for src, en in EN.items():
    data = open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb').read()
    recs = [r for r in G.extract(data, src) if r['id'].endswith('#39574')]
    assert len(recs) == 1
    rec = recs[0]
    rec['en'] = en
    p = os.path.join(ROOT, 'translation', src.replace('/', '__') + '.jsonl')
    raw = open(p, 'rb').read().decode('utf8')
    lines = raw.split('\n')
    if any(('"id":"%s"' % rec['id']) in l for l in lines):
        print('already there', rec['id']); continue
    open(os.path.join(ROOT, 'build', 's7', 'bak', os.path.basename(p) + '.s7t'), 'wb').write(raw.encode('utf8'))
    out = []; done = False
    for l in lines:
        if not done and l.strip():
            o = json.loads(l)
            if int(o['id'].rsplit('#', 1)[1], 16) > 0x39574:
                out.append(json.dumps(rec, ensure_ascii=False, separators=(',', ':'))); done = True
        out.append(l)
    assert done
    tmp = p + '.s7t.tmp'
    open(tmp, 'wb').write('\n'.join(out).encode('utf8'))
    os.replace(tmp, p)
    print('added', rec)
