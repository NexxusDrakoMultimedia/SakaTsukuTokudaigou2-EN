import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art1_install.py')
s = open(p, encoding='utf8').read()
s = s.replace("n = 0\n", "n = 0\nHELD = {'07332', '10469'}   # blocked by orphan text records inside their compressed streams (see report)\n")
s = s.replace("        for d in dests:\n", "        for d in dests:\n            if i in HELD and d != dests[0]:\n                d = os.path.join(B, 'held')\n")
open(p, 'w', encoding='utf8').write(s)
