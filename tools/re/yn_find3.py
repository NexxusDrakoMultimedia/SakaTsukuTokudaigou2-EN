import sys, os
root = sys.argv[1]
hai = bytes.fromhex('82cd82a2')
hai_le = bytes.fromhex('cd82a282')
ie = bytes.fromhex('82a282a282a6')   # いいえ? え = 82 A6 (hiragana e)
ie_le = bytes.fromhex('a282a282a682')
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        try: d = open(p, 'rb').read()
        except Exception: continue
        for nm, pat in (('hai', hai), ('hai_le', hai_le), ('iie', ie), ('iie_le', ie_le)):
            i = d.find(pat); c = 0; hs = []
            while i >= 0:
                hs.append(i); i = d.find(pat, i+1)
            if hs and (nm.startswith('iie') or len(hs) < 40) and os.path.getsize(p) < 6000000:
                print(os.path.relpath(p, root), nm, len(hs), [hex(h) for h in hs[:4]])
