p = 'tools/re/art7_specs_c.py'
s = open(p, encoding='utf-8').read()
s = s.replace("\nSPECS = {}\nfor _id", "EXTRA['00628'] = list(EXTRA['00344'])\n\nSPECS = {}\nfor _id", 1)
open(p, 'w', encoding='utf-8').write(s)
