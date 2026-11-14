"""Skeptic helper: mutate a scratch file in place.

usage: rel_skeptic_mut.py flip FILE OFFSET [XOR]   flip one byte
       rel_skeptic_mut.py trunc FILE NEWSIZE       truncate
Only ever point this at a scratch copy.
"""
import sys

mode, path = sys.argv[1], sys.argv[2]
if mode == "flip":
    off = int(sys.argv[3], 0)
    x = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x55
    with open(path, "r+b") as f:
        f.seek(off)
        b = f.read(1)
        f.seek(off)
        f.write(bytes([b[0] ^ x]))
elif mode == "trunc":
    with open(path, "r+b") as f:
        f.truncate(int(sys.argv[3], 0))
else:
    raise SystemExit("bad mode")
