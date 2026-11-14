# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""fin: club-name exhaustive check on the REAL overlays of a built trial disc (not of a --dump).

    python -I -X utf8 tools/re/fin_clubs.py TRIALDIR NAME [--keep]

TRIALDIR/NAME (Track N).bin are read through the ISO9660 directory of the disc itself (tools/gdrom.py with the track names replaced),
FLOW_PRG/BPMATCH.BIN and FLOW_PRG/HOMETOWN.BIN are written to build/fin_clubs_NAME/FLOW_PRG/ and the three existing censuses run on them:
pol_shapes.py (odd shapes), skp_census.py (independent odd-shape test), int_clubs.py (composer + popup join, problems).
The scratch folder is deleted unless --keep.  Exit code 1 when any census reports a problem or an odd shape.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import gdrom  # noqa: E402


def main():
    trial, name = sys.argv[1], sys.argv[2]
    keep = "--keep" in sys.argv
    gdrom.BASE = name + " (Track %d).bin"
    d = gdrom.Disc(trial)
    files = {p: (l, s) for p, l, s in gdrom.walk(d, *gdrom.pvd_root(d))}
    out = os.path.join(ROOT, "build", "fin_clubs_" + name)
    os.makedirs(os.path.join(out, "FLOW_PRG"), exist_ok=True)
    for f in ("BPMATCH.BIN", "HOMETOWN.BIN"):
        l, s = files["/FLOW_PRG/" + f]
        open(os.path.join(out, "FLOW_PRG", f), "wb").write(d.read(l, s))
        print("extracted /FLOW_PRG/%s %d bytes (LBA %d)" % (f, s, l))
    rc = 0
    for script in ("pol_shapes.py", "skp_census.py", "int_clubs.py"):
        print("\n######## %s %s" % (script, name), flush=True)
        p = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, script), out],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(p.stdout[-3500:])
        if p.stderr.strip():
            print(p.stderr[-800:])
        print("exit", p.returncode)
        rc |= 1 if p.returncode else 0
    if not keep:
        shutil.rmtree(out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
