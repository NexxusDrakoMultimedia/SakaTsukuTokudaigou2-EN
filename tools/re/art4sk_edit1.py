import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art4sk_plates.py')
s = open(p, encoding='utf8').read()
old = "            d = orig[y, xd]\n"
new = ("            d = orig[y, xd]\n"
       "            if rec == 1:\n"
       "                d = np.array(JEN.get(y, (0x55, 0x44, 0x11)) + (255,), np.uint8)\n")
assert old in s
s = s.replace(old, new)
s = s.replace("            if rec == 1 and y >= 31:", "            if rec == 1 and y >= 28:")
s = s.replace("BAR = {0, 1, 2, 3, 4, 8}\n", "BAR = {0, 1, 2, 3, 4, 8}\nJEN = {28: (0xee, 0xcc, 0x66), 29: (0xff, 0xee, 0x88), 30: (0xdd, 0xaa, 0x22), 31: (0xdd, 0xaa, 0x22), 32: (0xdd, 0xaa, 0x22), 33: (0xaa, 0x88, 0x22), 34: (0x66, 0x55, 0x11)}\n")
open(p, 'w', encoding='utf8').write(s)
