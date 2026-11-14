import sys, os
root = sys.argv[1]
pats = {'euc_iie': bytes.fromhex('a4a4a4a4a4a8'), 'jis_iie': bytes.fromhex('242424242428'), 'jis_iie_le': bytes.fromhex('242424242428'),
        'euc_hai': bytes.fromhex('a4cfa4a4'), 'jis_hai': bytes.fromhex('244f2424'), 'euc_iie2': bytes.fromhex('a4a4a1a1a4a4')}
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try: d = open(p, 'rb').read()
        except Exception: continue
        for k, v in pats.items():
            hs = []; i = d.find(v)
            while i >= 0 and len(hs) < 6: hs.append(i); i = d.find(v, i+1)
            if hs and k in ('euc_iie','jis_iie'): print(os.path.relpath(p, root), k, [hex(h) for h in hs])
