p = "tools/release.toml"
t = open(p, encoding="utf-8").read()
a = "# The release bundle carries the translators' notes (written by the docs stage)."
b = "# The release bundle carries the translators' notes and player guide (doc/TRANSLATORS_NOTES.md, real text since 0.1.0)."
assert a in t
open(p, "w", encoding="utf-8", newline="\n").write(t.replace(a, b))
