"""hng: split build/int/tsub/u1 (SCDRF.BIN + SEARCH.BIN, the three textures that hang) into one-file subsets v1..v3.

v1 = SCDRF.BIN/@2ff64#0; v2 = SEARCH.BIN/@2c58c#0; v3 = SEARCH.BIN/@2fcf0#0.
Usage: python -I -X utf8 tools/re/hng_mksub_u1.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'build', 'int', 'tsub', 'u1')
OUT = os.path.join(ROOT, 'build', 'int', 'tsub')
MAP = {'FLOW_PRG/SCDRF.BIN/@2ff64#0.pvr': 'v1',
       'FLOW_PRG/SEARCH.BIN/@2c58c#0.pvr': 'v2',
       'FLOW_PRG/SEARCH.BIN/@2fcf0#0.pvr': 'v3'}


def main():
    for g in MAP.values():
        d = os.path.join(OUT, g)
        if os.path.isdir(d):
            shutil.rmtree(d)
    for rel, g in MAP.items():
        src = os.path.join(SRC, rel)
        dst = os.path.join(OUT, g, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(g, rel, os.path.getsize(dst))


if __name__ == '__main__':
    main()
