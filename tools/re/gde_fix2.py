p = "tools/test_release.py"
t = open(p, encoding="utf-8").read()
a = "    test_py38()\n    ok = sum"
b = "    test_py38()\n    test_guide()\n    ok = sum"
assert a in t
t = t.replace(a, b)
a = " 5  the shipped player files parse as Python 3.8.\n"
b = a + " 6  the real translators' notes (doc/TRANSLATORS_NOTES.md): no PLACEHOLDER, main sections, hashes equal release.toml,\n    money examples add up, bundled unchanged into a tiny release.\n"
assert a in t
t = t.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(t)
