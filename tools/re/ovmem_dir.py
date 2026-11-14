"""ovmem: the directory-cache table of 1ST_READ.BIN (name ptr, entry count) vs real file counts of extracted/_filelist.tsv (read-only)."""
import collections, struct
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
def u32(a): return struct.unpack_from('<I', D, a - B)[0]
def cs(a):
    o = a - B
    e = D.index(b'\0', o)
    return D[o:e].decode('latin1')
real = collections.Counter()
for l in open('extracted/_filelist.tsv', encoding='utf8'):
    p = l.split('\t')[0].split('/')
    real[p[1] if len(p) > 2 else ''] += 1
a = 0x8c16c104
while True:
    w = u32(a)
    if not (0x8c16a000 <= w < 0x8c16c000): break
    n = cs(w)
    print('%-9s count_in_table=%4d  files_on_disc=%4d  slack=%d  (entry at %#x, words %s)' % (
        n, u32(a + 4), real.get(n, 0), u32(a + 4) - real.get(n, 0), a, [hex(u32(a + 4 * i)) for i in range(1, 4)]))
    a += 16
print('root files', real.get('', 0))
