# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_syn DIR: build a synthetic mini game under DIR (extracted/FLOW_PRG/SYN.BIN, translation/SYN.jsonl) with hostile strings:
invalid cp932 bytes, lone lead bytes, undefined double bytes, NEC/IBM extension characters, literal <3C>-like text, newlines,
identical Japanese at two offsets with different English.  Then the caller runs l10n export / import on it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import l10n

dest = os.path.abspath(sys.argv[1])
strings = [
    b'OK', b'OK', b'\x82\xa0\x82\xa2', b'\x82\xa0\x82\xa2',
    b'\xff\xfe', b'\x81', b'ab\x81', b'\x85\x40', b'\xed\x40', b'\xfa\x40', b'<3C>x', b'a<b>c', b'<41>', b'x\ny', b'\xa1\xb1\xdf',
    b'\x80', b'\xa0', b'\xfd\xfe', b'\x87\x40', b'\x81\x40', b'\x5c', b'\x7e\x7f', b'\xf0\x40', b'\x82\x41',
]
blob = bytearray(b'HDR\0')
recs = []
for k, s in enumerate(strings):
    off = len(blob)
    blob += s + b'\0'
    ja = l10n.decode_textdb(s)
    en = 'english %d' % k if k % 5 else ''
    recs.append({'id': 'FLOW_PRG/SYN.BIN#%x' % off, 'ja': ja, 'en': en, 'max_bytes': len(s), 'slot': 0, 'refs': None})
os.makedirs(os.path.join(dest, 'extracted', 'FLOW_PRG'), exist_ok=True)
os.makedirs(os.path.join(dest, 'translation'), exist_ok=True)
open(os.path.join(dest, 'extracted', 'FLOW_PRG', 'SYN.BIN'), 'wb').write(bytes(blob))
with open(os.path.join(dest, 'translation', 'FLOW_PRG__SYN.BIN.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
print('built', len(recs), 'records')
for r in recs:
    print(r['id'], repr(r['ja']))
