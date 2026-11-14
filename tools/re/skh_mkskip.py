"""skh: build a COPY of the translation DB in which the junk orphan records are skipped (skip:true), for a trial disc that tests the
code-overwrite finding.  The real translation/ directory is NOT touched.

usage: skh_mkskip.py OUTDIR [--dry]
Skip rule (all conditions): record is an orphan ('orphan (no pointer)'), has a non-empty en, is not already skipped, AND
  (a) its en is one of the placeholders written over binary data: '-', 'Plot', 'Misc', 'Bow'   (the 520 of docs/hang-investigation.md 2.6), or
  (b) it is one of the code-zone overwrites found by skh_codezone.py + manual disassembly: ENDING #29fb9 'Cma', NENREP #162 'Out R4',
      NEWMONTH #40290 'Pact' and #84ad6 'P/L', NEWS_ED #b99 'Home', YOUTH #4d9e '-' (also covered by a).
Copies every translation/*.jsonl (and other files) into OUTDIR, sets "skip": true on the matching records, prints per file counts and a total.
"""
import glob
import json
import os
import re
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

PLACEHOLDERS = {'-', 'Plot', 'Misc', 'Bow'}
CODE = {('FLOW_PRG/ENDING.BIN', 0x29fb9), ('FLOW_PRG/NENREP.BIN', 0x162), ('FLOW_PRG/NEWMONTH.BIN', 0x40290),
        ('FLOW_PRG/NEWMONTH.BIN', 0x84ad6), ('FLOW_PRG/NEWS_ED.BIN', 0xb99), ('FLOW_PRG/YOUTH.BIN', 0x4d9e)}


def main(argv):
    out = argv[1]
    dry = '--dry' in argv
    src = os.path.join(ROOT, 'translation')
    if not dry:
        os.makedirs(out, exist_ok=True)
    cnt = Counter()
    total = 0
    for p in sorted(glob.glob(os.path.join(src, '*'))):
        name = os.path.basename(p)
        if os.path.isdir(p):
            continue                      # art/ refit/ textures/ are NOT copied: the build reads jsonl files below --tdb recursively
        if not name.endswith('.jsonl'):
            if not dry:
                shutil.copy2(p, os.path.join(out, name))
            continue
        lines = []
        for ln in open(p, encoding='utf-8'):
            r = json.loads(ln)
            if r.get('orphan') and not r.get('skip') and (r.get('en') or '').strip():
                path, off = r['id'].split('#')
                off = int(off, 16)
                if r['en'] in PLACEHOLDERS or re.match(r'^[-_.?*/ ]+$', r['en']) or (path, off) in CODE:
                    r['skip'] = True
                    r['en'] = ''          # the build ignores 'skip' (merge hint only): an empty en keeps the original bytes
                    cnt[name] += 1
                    total += 1
                    ln = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n'
            lines.append(ln if ln.endswith('\n') else ln + '\n')
        if not dry:
            with open(os.path.join(out, name), 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(lines)
    print('skipped records: %d in %d files' % (total, len(cnt)))
    print(cnt.most_common(8))


if __name__ == '__main__':
    main(sys.argv)
