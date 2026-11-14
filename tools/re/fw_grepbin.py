"""fw_grepbin.py PATTERN [ROOT]: list files under ROOT (default extracted) that contain the ASCII/bytes PATTERN, with offsets (first 5)."""
import os, sys, re
pat = sys.argv[1].encode('latin-1')
root = sys.argv[2] if len(sys.argv) > 2 else 'extracted'
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try:
            if os.path.getsize(p) > 80_000_000:
                continue
            d = open(p, 'rb').read()
        except OSError:
            continue
        offs = [m.start() for m in re.finditer(re.escape(pat), d)]
        if offs:
            print(p, len(offs), [hex(o) for o in offs[:5]])
