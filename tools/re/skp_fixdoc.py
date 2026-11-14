"""skp: correct three counts in docs/layout-issues.md 9.9 (verified by tools/re/skp_perfile.py and skp_dups.py)"""
import os
p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'docs', 'layout-issues.md')
t = open(p, encoding='utf-8', newline='').read()
reps = [
 ("107 of the 1,248 town short forms (`tbl@43858`, the pointer table the composer reads) contained",
  "107 of the 1,270 slots of the town short table (`tbl@43858`, the pointer table the composer reads; the composer uses slots 1 to 1,248, so 106 of the 107 are reachable, `Kume Is` at slot 1,249 is not) contained"),
 ("(The stage-3 figure of 106 was one short.)", "(The stage-3 figure of 106 counted only the 1,248 slots the composer reads.)"),
 ("exist in **31 translation files**", "exist in **32 translation files**"),
 ("3,317 `en` values in all.", "3,424 `en` values (32 x 107) carry the new forms (checked by `tools/re/skp_perfile.py`)."),
]
for a, b in reps:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
open(p, 'w', encoding='utf-8', newline='').write(t)
print('ok')
