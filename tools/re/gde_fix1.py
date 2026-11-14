import io
p = "doc/TRANSLATORS_NOTES.md"
t = open(p, encoding="utf-8").read()
a = "| **Wk** | Week, in tight columns. Months are divided into weeks; `Early` and `Late` mark the two halves of a week-based schedule. |"
b = "| **Wk** | Week, in tight columns and calendars. |"
assert a in t; t = t.replace(a, b)
a = "`Yen` appears only for an\n  amount of exactly zero and for the few small amounts that are really counted in single yen."
b = "`Yen` appears for an\n  amount of exactly zero and on the unit pictures."
assert a in t; t = t.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(t)
