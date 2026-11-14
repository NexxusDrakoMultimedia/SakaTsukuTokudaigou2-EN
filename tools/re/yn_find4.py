import sys, os
pats = {'iie': bytes.fromhex('82a282a282a6'), 'iie_le': bytes.fromhex('a282a282a682'), 'hai': bytes.fromhex('82cd82a2'), 'hai_sp': bytes.fromhex('82cd814082a2')}
root = sys.argv[1]
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        if os.path.getsize(p) > 64000000: continue
        d = open(p, 'rb').read()
        for k, v in pats.items():
            hs = []; i = d.find(v)
            while i >= 0 and len(hs) < 8:
                hs.append(i); i = d.find(v, i + 1)
            if hs: print(p, k, [hex(h) for h in hs])
