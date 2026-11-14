"""tx5: fit the six style labels of the Event / scout info panel (SCDRF.BIN and SEARCH.BIN, tbl[0..4]) into the panel.

The Japanese labels are right-aligned in a 12-cell window (2 full-width spaces + 4 full-width chars = 12 cells; 1 space + 5 chars;
6 chars).  The panel draws monospace 12 px cells (the playtest showed '    Centre P': 4 spaces + 8 characters = 12), so every label
must be at most 12 characters INCLUDING the indent.  Old: '    Left Side' (13) lost a letter, '    Centre Push' (15) lost 'ush'.
New: the same words right-aligned to exactly 12 characters.

    python -I -X utf8 tools/re/tx5_fix_tactics.py [--write]
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
NEW = {
    'ポストプレー': '   Post Play',
    '　　左サイド': '   Left Side',
    '　　右サイド': '  Right Side',
    '　　中央突破': ' Centre Push',
    '　カウンター': '     Counter',
}
FILES = {'FLOW_PRG__SCDRF.BIN.jsonl': 'tbl@1cd14[', 'FLOW_PRG__SEARCH.BIN.jsonl': 'tbl@28110['}


def main():
    write = '--write' in sys.argv
    for fn, ctx in FILES.items():
        p = os.path.join(ROOT, 'translation', fn)
        out = []
        n = 0
        with open(p, encoding='utf-8', newline='') as f:
            for line in f:
                body = line.rstrip('\r\n')
                eol = line[len(body):]
                if body.strip():
                    r = json.loads(body)
                    if r['ja'] in NEW and r.get('ctx', '').startswith(ctx) and r['en'] != NEW[r['ja']]:
                        assert len(NEW[r['ja']]) <= 12
                        old = r['en']
                        r['en'] = NEW[r['ja']]
                        nb = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
                        print('%s %s: %r -> %r' % (fn, r['id'], old, r['en']))
                        body = nb
                        n += 1
                out.append(body + eol)
        if write and n:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(''.join(out))
    print('done', '(written)' if write else '(dry run)')


if __name__ == '__main__':
    main()
