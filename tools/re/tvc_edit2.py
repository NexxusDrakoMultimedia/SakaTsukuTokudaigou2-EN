"""tvc_edit2.py : clean-up edit of tools/moneypatch.py (remove a leftover no-op, check the text-constructor literal)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moneypatch.py')
s = open(p, encoding='utf8').read()
a = s.index("    if struct.unpack_from('<II', d, t['lit_text'])[0] != 0x8C2D4930")
b = s.index("    code, tail, _ = tv_card_bytes(t['base'] + money_off)")
s = s[:a] + "    if struct.unpack_from('<I', d, t['lit_text'])[0] != 0x8C2D4930:\n        raise MoneyPatchError('%s: TV card text-object constructor literal changed' % name)\n" + s[b:]
tmp = p + '.tmp'
open(tmp, 'w', encoding='utf8', newline='\n').write(s)
os.replace(tmp, p)
