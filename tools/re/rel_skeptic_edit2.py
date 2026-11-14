import os
p = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/tools/verify_dist.py'
s = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")
old = '''        check(not bad and n > 0, "SHA256SUMS: %d files verified%s" % (n, "" if not bad else ", BAD: %s" % bad))
'''
new = '''        check(not bad and n > 0, "SHA256SUMS: %d files verified%s" % (n, "" if not bad else ", BAD: %s" % bad))
        # nothing may sit in the folder that SHA256SUMS does not list (a stray file would be shipped with the folder)
        listed = set()
        with open(sums, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    listed.add(line.rstrip("\n").split("  ", 1)[1].replace("\\\\", "/"))
        stray = []
        for root, dirs, files in os.walk(dist):
            dirs[:] = [d for d in dirs if d != "__pycache__"]          # bytecode of a run from here; never in the zip
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), dist).replace("\\\\", "/")
                if rel not in listed and rel != "SHA256SUMS":
                    stray.append(rel)
        check(not stray, "no file outside SHA256SUMS%s" % ("" if not stray else ": %s" % sorted(stray)))
'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
