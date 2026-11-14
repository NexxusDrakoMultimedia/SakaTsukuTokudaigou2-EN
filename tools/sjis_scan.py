import os, re, sys, collections
# runs of >=4 SJIS chars (kana/kanji lead bytes 81-9F,E0-EA + valid trail)
pat = re.compile(rb'(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){0}(?:(?:[\x82][\x9f-\xf1\x4f-\x58\x60-\x79\x81-\x9a])|(?:[\x83][\x40-\x96])|(?:[\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc])|\x81[\x40-\xac]){4,}')
root = sys.argv[1]; res = []
for dp, _, fns in os.walk(root):
    for fn in fns:
        p = os.path.join(dp, fn)
        if os.path.getsize(p) > 80_000_000: continue
        d = open(p, "rb").read(); n = 0; ch = 0; ok = 0
        for m in pat.finditer(d):
            try: m.group().decode("cp932"); ok += 1; ch += len(m.group())//2
            except: pass
        if ok: res.append((ch, ok, os.path.getsize(p), os.path.relpath(p, root).replace("\\", "/")))
res.sort(reverse=True)
for r in res[:60]: print("%7d chars %6d runs %10d bytes  %s" % r)
print(len(res), "files with SJIS runs")
