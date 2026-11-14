# SPDX-License-Identifier: GPL-3.0-or-later
"""List the tools/re helper-script families (prefix, count, first docstring line of each file).

Usage: python -I -X utf8 tools/re/doc_prefixes.py [--all]
Read-only; used to keep the family table in docs/helper-scripts.md honest.
"""
import ast
import warnings
import os
import sys

warnings.simplefilter("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))


def first_line(path):
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        d = ast.get_docstring(tree)
        if d:
            return d.strip().splitlines()[0][:110]
    except Exception:
        pass
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("#") and "SPDX" not in ln and "Copyright" not in ln and ln.strip("# \n"):
                    return ln.strip("# \n")[:110]
    except Exception:
        pass
    return ""


def main():
    show_all = "--all" in sys.argv
    fam = {}
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), HERE).replace("\\", "/")
            base = os.path.basename(rel)
            pre = base.split("_", 1)[0] if "_" in base else base[:-3]
            if "/" in rel:
                pre = rel.split("/")[0] + "/"
            fam.setdefault(pre, []).append(rel)
    for pre in sorted(fam):
        files = fam[pre]
        print("%-12s %3d  %s" % (pre, len(files), first_line(os.path.join(HERE, files[0]))))
        if show_all:
            for r in files:
                print("      %-40s %s" % (r, first_line(os.path.join(HERE, r))))


main()
