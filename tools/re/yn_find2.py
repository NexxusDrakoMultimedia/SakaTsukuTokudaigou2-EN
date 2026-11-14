import sys, os, re
root = sys.argv[1]
ha = 'は'.encode('cp932'); i_ = 'い'.encode('cp932'); e_ = 'え'.encode('cp932')
rx = re.compile(re.escape(ha) + rb'[\x20\x81\x40]{1,4}' + re.escape(i_) + rb'(?!' + re.escape(i_) + b')')
rx2 = re.compile(re.escape(i_) + rb'[\x20]{0,2}(?:' + re.escape(i_) + rb')[\x20]{0,2}' + re.escape(e_))
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try: d = open(p, 'rb').read()
        except Exception: continue
        for name, r in (('hai', rx), ('iie', rx2)):
            hs = [m.start() for m in r.finditer(d)]
            if hs: print(os.path.relpath(p, root), name, len(hs), [hex(h) for h in hs[:5]])
