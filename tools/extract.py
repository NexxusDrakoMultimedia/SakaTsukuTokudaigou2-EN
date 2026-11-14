import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gdrom
out = sys.argv[1] if len(sys.argv) > 1 else "extracted"
skip = ("/BCAST/BCAST.BIN",)
d = gdrom.Disc(); fs = list(gdrom.walk(d, *gdrom.pvd_root(d)))
# also dump the IP.BIN (first 16 sectors of track 3, system area)
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "IP.BIN"), "wb").write(d.read(45000, 16*2048))
with open(os.path.join(out, "_filelist.tsv"), "w") as m:
    for p, l, s in fs:
        m.write(f"{p}\t{l}\t{s}\n")
        if p in skip: continue
        dst = os.path.join(out, p.lstrip("/")); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(d.read(l, s))
print(len(fs), "files")
