import sys, os
pats = {
 'hai': 'はい'.encode('cp932'),
 'ha_sp_i': 'は　い'.encode('cp932'),
 'iie': 'いいえ'.encode('cp932'),
 'iie_sp': 'い　い　え'.encode('cp932'),
}
root = sys.argv[1]
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try:
            d = open(p, 'rb').read()
        except Exception:
            continue
        for k, v in pats.items():
            i = 0; hits = []
            while True:
                i = d.find(v, i)
                if i < 0: break
                hits.append(i); i += 1
            if hits and k in ('iie','iie_sp','ha_sp_i'):
                print(os.path.relpath(p, root), k, len(hits), [hex(h) for h in hits[:6]])
