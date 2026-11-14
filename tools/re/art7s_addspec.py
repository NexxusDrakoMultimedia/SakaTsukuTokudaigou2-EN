import re
p = 'tools/re/art7_specs_c.py'
s = open(p, encoding='utf-8').read()
add = """
# skeptic pass: leftover kanji on dr_comm atlas #0 (00344)
EXTRA['00344'] = [
    dict(rect=(244, 130, 22, 28), text='th', mode='outline', font='arial-bold', pad=0, erase={'mode': 'clear'}, erase_grow=[1, 1, 1, 1], style=WHT),
    dict(rect=(304, 395, 30, 26), text='Yr', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
]
"""
s = s.replace("\nSPECS = {}\nfor _id", add + "\nSPECS = {}\nfor _id", 1)
open(p, 'w', encoding='utf-8').write(s)
