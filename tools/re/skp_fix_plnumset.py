"""skp (skeptic): fix the two PLNUMSET strings of the right-hand player panel (shirt number screen), by record id.

The panel is a 4 row x 12 cell buffer (FLOW_PRG/PLNUMSET.BIN builder at 0x1302): blank filled, `sprintf(b + 13, label)`,
`sprintf(b + 31, "%s %2d歳")`, then the game writes a newline at bytes 12, 25 and 38 and a NUL at 51.
  * row 1 label (`#34b74`, with number; `#34b64` without) must be EXACTLY 12 characters after expansion: its NUL has to land on byte 25 where the
    newline is written afterwards.  Longer: the last digit is overwritten by the newline and the NUL ends the whole text; shorter: the NUL stays
    inside the row and ends the text, the position / age row below is never shown.  Old English ` Shirt No. %2d ` = 14 characters.
  * the position + age text (`#34b84`) starts at byte 31 (column 5 of row 2) and has 7 characters in Japanese (`DF 25歳`): it must have 7 at most
    (the newline at byte 38 would eat the first digit of a longer text and the NUL would land in row 3).  Old English `%s Age %2d` = 9 characters.

    python -I -X utf8 tools/re/skp_fix_plnumset.py [--dry]

One read-modify-write of translation/FLOW_PRG__PLNUMSET.BIN.jsonl (other workflows edit other records of the translation files), atomic replace,
only the `en` field of the two records changes; re-run is a no-op.
"""
import json, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, 'translation', 'FLOW_PRG__PLNUMSET.BIN.jsonl')
NEW = {
    'FLOW_PRG/PLNUMSET.BIN#34b74': (' Shirt No. %2d ', ' Shirt No.%2d'),
    'FLOW_PRG/PLNUMSET.BIN#34b84': ('%s Age %2d', '%s %2dyo'),
}


def expanded(fmt):
    return len(fmt.replace('%s', 'DF').replace('%2d', '12'))


def main():
    dry = '--dry' in sys.argv
    raw = open(PATH, 'rb').read()
    text = raw.decode('utf-8')
    lines = text.split('\n')
    n = 0
    for i, ln in enumerate(lines):
        for rid, (old, new) in NEW.items():
            if ln.startswith('{"id":"%s"' % rid):
                r = json.loads(ln)
                assert json.dumps(r, ensure_ascii=False, separators=(',', ':')) == ln.rstrip('\r'), 'record formatting differs: ' + rid
                if r['en'] == new:
                    print('already', rid, repr(new))
                    continue
                assert r['en'] == old, 'unexpected en for %s: %r' % (rid, r['en'])
                r['en'] = new
                lines[i] = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + ('\r' if ln.endswith('\r') else '')
                n += 1
                print('%s: %r (%d chars expanded) -> %r (%d)' % (rid, old, expanded(old), new, expanded(new)))
    assert expanded(NEW['FLOW_PRG/PLNUMSET.BIN#34b74'][1]) == 12 and expanded(NEW['FLOW_PRG/PLNUMSET.BIN#34b84'][1]) <= 7
    if dry or not n:
        return
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PATH), prefix='.skp_', suffix='.tmp')
    with os.fdopen(fd, 'wb') as f:
        f.write('\n'.join(lines).encode('utf-8'))
    os.replace(tmp, PATH)


main()
