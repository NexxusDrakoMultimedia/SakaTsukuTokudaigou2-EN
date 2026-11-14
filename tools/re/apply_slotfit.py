"""Apply slot-specific English forms from TSV files to records that still have no English.
   python -I -X utf8 tools/re/apply_slotfit.py FILE.tsv [FILE.tsv ...] [--dry-run]
Each line:  ja <TAB> slot_bytes <TAB> en     (slot_bytes = the record's max_bytes, NUL included)
Checks: en is printable ASCII, len(en) + 1 <= slot_bytes, en not empty.  A form is written to every record with that ja,
that exact max_bytes and an empty en (never overwrites).  Prints what applied and what was rejected."""
import glob, json, os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dry = '--dry-run' in sys.argv
paths = [a for a in sys.argv[1:] if not a.startswith('--')]
forms = {}
bad = 0
for p in paths:
    with open(p, encoding='utf8') as fh:
        for n, line in enumerate(fh, 1):
            line = line.rstrip('\r\n')
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) != 3 or not parts[1].isdigit():
                print('%s:%d malformed' % (p, n)); bad += 1; continue
            ja, slot, en = parts[0], int(parts[1]), parts[2]
            if not en.strip() or any(not (0x20 <= ord(c) <= 0x7e) for c in en) or len(en) + 1 > slot:
                print('%s:%d rejected %r slot %d: %r' % (p, n, ja, slot, en)); bad += 1; continue
            forms[(ja, slot)] = en
applied = 0
for f in sorted(glob.glob(os.path.join(root, 'translation', '*.jsonl'))):
    with open(f, encoding='utf8', newline='') as fh:
        lines = fh.read().split('\n')
    changed = False
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        r = json.loads(ln)
        if (r.get('en') or '').strip() or r.get('skip'):
            continue
        en = forms.get((r['ja'], r.get('max_bytes')))
        if en is None:
            continue
        r['en'] = en
        lines[i] = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
        applied += 1
        changed = True
    if changed and not dry:
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write('\n'.join(lines))
        os.replace(tmp, f)
print('%s: %d forms loaded, %d records filled, %d lines rejected' % ('dry run' if dry else 'applied', len(forms), applied, bad))
sys.exit(1 if bad else 0)
