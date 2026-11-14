p = 'tools/re/art6_gen_match.py'
s = open(p, encoding='utf8').read()
s = s.replace("{'mode': 'vgrad'}, maxs=19, erase_rect=[10, 42 + 32 * k, 116, 26]", "clr, maxs=19, erase_rect=[11, 41 + 32 * k, 114, 28]")
open(p, 'w', encoding='utf8').write(s)
