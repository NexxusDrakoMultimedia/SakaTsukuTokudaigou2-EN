# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_leak DIR: write hostile working files (Japanese hiding in en / ctx / why / extra keys, unencodable ja, compat CJK
characters) under DIR/translation_N and print what the exporter says about each.  Nothing outside DIR is touched."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dest = os.path.abspath(sys.argv[1])
cases = {
    'kana_en': {'en': 'x \u3042 y'},
    'kanji_en': {'en': '\u7e8a'},
    'fullwidth_en': {'en': '\uff21\uff22'},
    'halfkana_en': {'en': '\uff71'},
    'kk_ctx': {'en': 'ok', 'ctx': '\u3042'},
    'why': {'en': 'ok', 'why': '\u6f22'},
    'squared_en': {'en': '\u3231 \u334c'},          # (kabu) and a squared katakana word: cp932 characters outside the old range
    'enclosed_en': {'en': '\u3220'},
    'cjk_radical_en': {'en': '\u2f00'},
    'box_en': {'en': '\u25a0\u2605\u203b'},          # legitimately Japanese-typography symbols; allowed or not is a policy question
    'extra_key': {'en': 'ok', 'note': '\u3042'},
    'ja_unencodable': {'en': 'ok', 'ja': 'caf\u00e9 \u20ac'},
}
os.makedirs(dest, exist_ok=True)
for name, extra in cases.items():
    d = os.path.join(dest, name, 'translation')
    os.makedirs(d, exist_ok=True)
    rec = {'id': 'FLOW_PRG/SYN.BIN#4', 'ja': 'OK', 'en': 'OK', 'max_bytes': 2, 'slot': 0, 'refs': None}
    rec.update(extra)
    with open(os.path.join(d, 'FLOW_PRG__SYN.BIN.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(ROOT, 'tools', 'l10n.py'), 'export', '--tdb', d,
                        '--out', os.path.join(dest, name, 'l10n'), '--only', 'SYN'], capture_output=True, text=True, encoding='utf-8')
    out = (r.stdout + r.stderr).strip().replace('\n', ' | ')
    print('%-16s exit=%d  %s' % (name, r.returncode, ascii(out[:120])))
    p = os.path.join(dest, name, 'l10n', 'FLOW_PRG__SYN.BIN.jsonl')
    if os.path.isfile(p):
        print('     WROTE:', ascii(open(p, encoding='utf-8').read().split('\n')[1][:100]))
