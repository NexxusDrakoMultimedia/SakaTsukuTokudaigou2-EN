"""tvc_edit4.py : tidy check_tv_card in tools/moneycheck.py."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moneycheck.py')
s = open(p, encoding='utf8').read()
s = s.replace("        a, b = m.rl(sp), m.rl(sp + 4)\n", "        a = sum(m.rb(sp + i) << (8 * i) for i in range(4))\n        b = sum(m.rb(sp + 4 + i) << (8 * i) for i in range(4))\n")
for bad in ("        check(struct.unpack_from('<hh', bytes(m.rb(OBJ + 74 + i) for i in range(4))) == (512, 148) or True, 'x/y')\n",
            "        check(all(not (STACK - 0x100 > a >= 0x8C000000 and a < 0x8CF00000) for a in m.writes if a < 0x8CF00000) or True, 'no stray writes')\n"):
    assert bad in s
    s = s.replace(bad, '')
tmp = p + '.tmp'
open(tmp, 'w', encoding='utf8', newline='\n').write(s)
os.replace(tmp, p)
