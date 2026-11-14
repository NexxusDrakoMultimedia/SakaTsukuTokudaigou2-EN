"""Debug: why does the repack self-check fail on FLOW_PRG/NEWS_OP.BIN with a fully translated overlay?"""
import sys, os, json, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py'))
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
import textdb as T, textrepack as R, struct
src = 'FLOW_PRG/NEWS_OP.BIN'
img = T.load_image(src)
ex = T.extract_image(img)
strs = ex[0]
recs = [json.loads(l) for l in open('build/synth_full/FLOW_PRG__NEWS_OP.BIN.jsonl', encoding='utf8')]
new, rp = R.repack(img.data, img.base, recs, source=src, extracted=ex)
by = {s.off: s for s in strs}
s = by[0x28f00]
print('str 0x28f00 off,max_bytes,refs,orphan,pinned,interior', hex(s.off), s.max_bytes, [hex(w) for w in s.refs], s.orphan, s.pinned, s.interior)
w = 0x28f20
print('word before', hex(struct.unpack_from('<I', img.data, w)[0]), 'after', hex(struct.unpack_from('<I', new, w)[0]))
# which string regions contain the pointer word?
for t in strs:
    if t.off <= w < t.off + t.max_bytes:
        print('word lies in region of str %#x max_bytes %d movable %s refs %s raw %r' % (t.off, t.max_bytes, R.is_movable(t), [hex(x) for x in t.refs][:4], t.raw[:30]))
pools, where = R.find_pools(strs)
for p in pools:
    if p.a <= w < p.z:
        print('word lies in pool %#x..%#x with %d strings' % (p.a, p.z, len(p.home)))
print('bytes around old:', img.data[0x28ee0:0x28f40].hex())
print('rep.ref_words has w', w in rp.ref_words)
bad = R.check(img.data, new, img.base, strs, R._entry_enc(recs, by, R.Report(src), src), rp)
print(bad[:5])
print('--- who covers 0x28f20 after repack?')
enc = R._entry_enc(recs, by, R.Report(src), src)
for t in strs:
    if 0x28f20 in t.refs:
        print('ref owner', hex(t.off))
for off, n in rp.layout.items():
    b = enc.get(off, by[off].raw)
    if n <= 0x28f20 < n + len(b) + 1:
        t = by[off]
        print('string orig %#x -> new %#x len %d covers it; orig max_bytes %d refs %s' % (off, n, len(b), t.max_bytes, [hex(x) for x in t.refs]))
for t in strs:
    if t.off <= 0x28f20 < t.off + 40 or 0x28ee0 <= t.off < 0x28f40:
        print('near: off %#x max %d movable %s pinned %s refs %s raw %r' % (t.off, t.max_bytes, R.is_movable(t), t.pinned, [hex(x) for x in t.refs][:3], t.raw[:24]))
print([ (hex(p.a), hex(p.z)) for p in pools if 0x28000 <= p.a <= 0x29800])
