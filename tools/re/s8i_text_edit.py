"""s8i: stage 8b text leftovers, by record id (read-modify-write, atomic replace, never BCAST).

  OPTION.BIN   日程進行 -> 'Advance Schedule', 終了・設定 -> 'Quit / Options'   (the repainted town-menu plates 08663 / 08805 and the help text)
  PLNUMSET#34b74 ' Squad No.%2d'                                               (12 cells after %2d expands; same wording as #34b64 ' Squad No.  ')
  G_INCOME#26490  万 -> 'man'                                                  (lower-case unit, was the western '0k')
  NENREP#24ef8   '333?@R/%soku %sman@'                                         (20 byte slot: 4 byte float prefix + 15 characters + NUL)
  NENREP gap records (textfmt_gap.GAPS, in-place, same slots as the Japanese pieces of the annual-report money formats):
     #24f0c %s億%s万円 -> '%soku %sman'   #24f18 @R/%s万円@ -> '@R/%s man@'   #24f24 %s万円 -> '%s man'   #24f2c %s円 -> '%s Yen'

    python -I -X utf8 tools/re/s8i_text_edit.py [--dry]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_gap as G   # noqa: E402

EDITS = {
    'FLOW_PRG/OPTION.BIN#88f4': 'Advance Schedule',
    'FLOW_PRG/OPTION.BIN#8b9c': 'Quit / Options',
    'FLOW_PRG/PLNUMSET.BIN#34b74': ' Squad No.%2d',
    'FLOW_PRG/G_INCOME.BIN#26490': 'man',
    'FLOW_PRG/NENREP.BIN#24ef8': '333?@R/%soku %sman@',
}
GAP_EN = {
    'FLOW_PRG/NENREP.BIN#24f0c': '%soku %sman',
    'FLOW_PRG/NENREP.BIN#24f18': '@R/%s man@',
    'FLOW_PRG/NENREP.BIN#24f24': '%s man',
    'FLOW_PRG/NENREP.BIN#24f2c': '%s Yen',
}


def dump(r, spaced):
    return json.dumps(r, ensure_ascii=False, separators=(', ', ': ') if spaced else (',', ':'))


def edit_file(path, edits, gap_new=None, dry=False):
    with open(path, encoding='utf8', newline='') as f:
        text = f.read()
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(nl)
    trailing = lines[-1] == ''
    if trailing:
        lines = lines[:-1]
    out, done = [], set()
    for ln in lines:
        r = json.loads(ln)
        spaced = '"id": ' in ln
        if r['id'] in edits:
            r['en'] = edits[r['id']]
            done.add(r['id'])
            ln = dump(r, spaced)
        out.append(ln)
    missing = set(edits) - done
    if missing:
        raise SystemExit('ids not found: %s' % sorted(missing))
    if gap_new:
        have = {json.loads(x)['id'] for x in out}
        ins = [g for g in gap_new if g['id'] not in have]
        for g in ins:
            off = int(g['id'].rsplit('#', 1)[1], 16)
            pos = len(out)
            for i, x in enumerate(out):
                if int(json.loads(x)['id'].rsplit('#', 1)[1], 16) > off:
                    pos = i
                    break
            out.insert(pos, dump(g, False))
    new = nl.join(out) + (nl if trailing else '')
    if not dry:
        tmp = path + '.s8i.tmp'
        with open(tmp, 'w', encoding='utf8', newline='') as f:
            f.write(new)
        os.replace(tmp, path)
    return len(done)


def main():
    dry = '--dry' in sys.argv
    by = {}
    for i, v in EDITS.items():
        by.setdefault(i.rsplit('#', 1)[0], {})[i] = v
    # new gap entries first: add them to textfmt_gap.GAPS in memory only to build the records (the source file carries them too)
    src = 'FLOW_PRG/NENREP.BIN'
    with open(os.path.join(ROOT, 'extracted', *src.split('/')), 'rb') as f:
        data = f.read()
    recs = [r for r in G.extract(data, src) if r['id'] in GAP_EN]
    if len(recs) != len(GAP_EN):
        raise SystemExit('textfmt_gap.GAPS does not yet hold the four NENREP money entries (%d found)' % len(recs))
    for r in recs:
        r['en'] = GAP_EN[r['id']]
    for source, ed in sorted(by.items()):
        assert 'BCAST' not in source
        path = os.path.join(ROOT, 'translation', source.replace('/', '__') + '.jsonl')
        n = edit_file(path, ed, recs if source == src else None, dry)
        print('%s: %d record(s) edited%s' % (source, n, ' (dry)' if dry else ''))


if __name__ == '__main__':
    main()
