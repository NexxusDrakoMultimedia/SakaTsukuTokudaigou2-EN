"""Apply build/hnm_names.json (full municipality names) and the '%s %s' message formats to translation/*.jsonl (atomic rewrite).

    python -I -X utf8 tools/re/hnm/hnm_apply_names.py [--dry]

Records touched
  * every translation/FLOW_PRG__*.jsonl record whose ctx is a municipality pointer table (`tbl@<hex>[i/1270]`) and whose ja is in the map;
  * FLOW_PRG__HOMETOWN.BIN.jsonl: the 126-byte record name fields (offsets 0x15972 + 126 k, max_bytes 35: recarr + orphan records);
  * a table record pinned in place by an interior pointer (`interior-ptrs` in ctx) keeps its old form when the new one does not fit its slot
    (AUTOSAVE 八戸市, EVENT 奥尻郡).
Other lines are copied byte for byte.  Prints one summary line per changed file.
"""
import glob
import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DRY = '--dry' in sys.argv
names = json.load(open(os.path.join(ROOT, 'build', 'hnm_names.json'), encoding='utf-8'))
TBL = re.compile(r'^tbl@[0-9a-f]+\[\d+/(1270|1268)\]')
BASE = 0x15972
MSG = {
    'FLOW_PRG/HOMETOWN.BIN#46e74': '%s %s.',
    'FLOW_PRG/HOMETOWN.BIN#46f84': 'Our club is now officially named\n@Y/"%s"@.\nOur home town is @K/"%s %s"@.',
    'FLOW_PRG/HOMETOWN.BIN#46fd1': 'The rival club has chosen\n@Y/"%s %s"@ as its home town.\nIts official name is @K/"%s"@.',
}


def is_name_field(rid, rec):
    if not rid.startswith('FLOW_PRG/HOMETOWN.BIN#'):
        return False
    off = int(rid.split('#')[1], 16)
    return rec.get('max_bytes') == 35 and off >= BASE and (off - BASE) % 126 == 0


total = 0
for path in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
    raw = open(path, 'rb').read().decode('utf-8')
    lines = raw.split('\n')
    out = []
    n = 0
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        rec = json.loads(ln)
        rid = rec['id']
        new = None
        if rid in MSG:
            new = MSG[rid]
        elif rec['ja'] in names and (TBL.match(rec.get('ctx') or '') or is_name_field(rid, rec)):
            new = names[rec['ja']]
            if new.endswith('-gun') and TBL.match(rec.get('ctx') or ''):
                new = new[:-4]                  # pointer-table records are the COMPOSITION form: no -gun (tools/re/hnm/hnmg_apply.py); the 126-byte name fields keep it
        if new is not None and 'interior-ptrs' in (rec.get('ctx') or '') and len(new.encode('cp932')) + 1 > rec['max_bytes']:
            new = None
        if new is not None and new != rec['en']:
            rec['en'] = new
            ln = json.dumps(rec, ensure_ascii=False, separators=(',', ':'))
            n += 1
        out.append(ln)
    if n:
        total += n
        print('%-46s %d records' % (os.path.basename(path), n))
        if not DRY:
            tmp = path + '.tmp'
            open(tmp, 'wb').write('\n'.join(out).encode('utf-8'))
            for attempt in range(20):               # another process may hold the file for a moment (Windows)
                try:
                    os.replace(tmp, path)
                    break
                except PermissionError:
                    time.sleep(0.5)
            else:
                raise SystemExit('cannot replace %s' % path)
print('total', total, '(dry run)' if DRY else '')
