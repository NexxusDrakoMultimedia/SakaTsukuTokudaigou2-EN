"""s8fg: byte ranges that differ between the ORIGINAL overlay and a disc copy (build/s8fg/<disc>/FILE) and are NOT inside any
database record's original extent (id .. id+max(slot,max_bytes,len(ja bytes))).  Those are pointer words, code hooks, caves, textures
or defects (a text write that landed on non-text data).
usage: s8fg_uncovered.py DISC FILE [MINBYTES=1]   e.g. s8e_nofix FLOW_PRG/SCDRF.BIN"""
import json, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
disc, rel = sys.argv[1], sys.argv[2]
a = open(os.path.join(ROOT, 'build', 's8fg', 'orig', rel), 'rb').read()
b = open(os.path.join(ROOT, 'build', 's8fg', disc, rel), 'rb').read()
jp = os.path.join(ROOT, 'translation', rel.replace('/', '__') + '.jsonl')
ext = []
for l in open(jp, encoding='utf-8'):
    if not l.strip():
        continue
    r = json.loads(l)
    off = int(r['id'].split('#')[1], 16)
    n = max(r.get('slot') or 0, r.get('max_bytes') or 0, len((r.get('ja') or '').encode('cp932', 'replace')) + 1)
    ext.append((off, off + n))
ext.sort()
# merge
m = []
for s, e in ext:
    if m and s <= m[-1][1]:
        m[-1][1] = max(m[-1][1], e)
    else:
        m.append([s, e])
import bisect
starts = [s for s, e in m]
def covered(i):
    k = bisect.bisect_right(starts, i) - 1
    return k >= 0 and m[k][0] <= i < m[k][1]
out = []
cur = None
for i in range(min(len(a), len(b))):
    if a[i] != b[i] and not covered(i):
        if cur and i - cur[1] <= 8:
            cur[1] = i + 1
        else:
            if cur: out.append(cur)
            cur = [i, i + 1]
if cur: out.append(cur)
print(rel, disc, 'uncovered ranges', len(out), 'bytes', sum(e - s for s, e in out))
for s, e in out:
    seg = b[s:e]
    w = struct.unpack_from('<I', b, s & ~3)[0] if len(b) > (s & ~3) + 4 else 0
    print('  %06x-%06x %5d  %s' % (s, e, e - s, seg[:24].hex()))

# classification: ranges whose every changed byte lies in an aligned word that is 0x8cXXXXXX in both the original and the disc copy are pointer rewrites
print('-- not pointer-word rewrites:')
for s, e in out:
    ok = True
    for i in range(s, e):
        if a[i] != b[i]:
            w0 = struct.unpack_from('<I', a, i & ~3)[0]
            w1 = struct.unpack_from('<I', b, i & ~3)[0]
            if not (0x8c000000 <= w0 < 0x8d000000 and 0x8c000000 <= w1 < 0x8d000000):
                ok = False
                break
    if not ok:
        print('  %06x-%06x %5d  old %s new %s' % (s, e, e - s, a[s:e][:20].hex(), b[s:e][:20].hex()))
