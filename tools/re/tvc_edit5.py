"""tvc_edit5.py : length bound in check_tv_card."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moneycheck.py')
s = open(p, encoding='utf8').read()
old = "            check(len(txt) <= 9, 'V=%d: at most 9 characters (%r)' % (V, txt))\n"
new = "            check(len(txt) <= (9 if V <= 9450000 else 15), 'V=%d: fits the field / the 16-byte buffer (%r)' % (V, txt))\n"
assert old in s
s = s.replace(old, new)
tmp = p + '.tmp'
open(tmp, 'w', encoding='utf8', newline='\n').write(s)
os.replace(tmp, p)
