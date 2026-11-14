import sys, os, re
root = sys.argv[1]
pats = {
 'ha_x_i_le': re.compile(rb'\xcd\x82(?:\x40\x81|\x20\x00|\x20\x20|\x00\x00)?\xa2\x82', re.S),
 'ii_e_le': re.compile(rb'\xa2\x82\xa2\x82\xa6\x82|\xa2\x82[\x00-\x20\x40\x81]{0,2}\xa2\x82[\x00-\x20\x40\x81]{0,2}\xa6\x82', re.S),
 'ii_e_be': re.compile(rb'\x82\xa2[\x00\x20\x81\x40]{0,2}\x82\xa2[\x00\x20\x81\x40]{0,2}\x82\xa6', re.S),
}
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try: d = open(p, 'rb').read()
        except Exception: continue
        for k, rx in pats.items():
            hs = [m.start() for m in rx.finditer(d)]
            if hs and k != 'ha_x_i_le': print(os.path.relpath(p, root), k, len(hs), [hex(h) for h in hs[:5]])
            elif hs and len(hs) < 6: print(os.path.relpath(p, root), k, len(hs), [hex(h) for h in hs[:5]])
