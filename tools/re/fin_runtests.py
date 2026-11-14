# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Run every cheap tools/test_*.py one after another and print one line each (name, exit code, seconds, last line).

    python -I -X utf8 tools/re/fin_runtests.py [name ...]

Without names it runs all test_*.py except test_pipeline.py (the long integrator test).  Exit code 1 if any fails.
"""
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
SKIP = {"test_pipeline.py"}


def main():
    names = sys.argv[1:]
    files = sorted(TOOLS.glob("test_*.py"))
    if names:
        files = [f for f in files if f.stem in names or f.name in names]
    else:
        files = [f for f in files if f.name not in SKIP]
    bad = 0
    for f in files:
        t = time.time()
        p = subprocess.run([sys.executable, "-I", "-X", "utf8", str(f)], cwd=str(TOOLS.parent),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (p.stdout + p.stderr).strip().splitlines()
        last = out[-1] if out else ""
        print("%-28s exit %d  %6.1fs  %s" % (f.name, p.returncode, time.time() - t, last[:110]), flush=True)
        if p.returncode != 0:
            bad += 1
            print("\n".join(out[-15:]), flush=True)
    print("FAILED: %d of %d" % (bad, len(files)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
