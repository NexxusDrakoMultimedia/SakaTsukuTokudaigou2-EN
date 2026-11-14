import os, sys, struct, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
img = open(sys.argv[1], 'rb').read()
def cs(o): return img[o:img.index(b'\0', o)].decode('cp932', 'replace')
for o in (0x3bc40, 0x34ff8, 0x35cc4, 0x375de, 0x1eba0):
    print(hex(o), cs(o))
for o in (0x46e74, 0x46f84, 0x46fd1):
    print(hex(o), cs(o).replace('\n', ' / '))
# longest English names in the pointer table / records
tl = [cs(struct.unpack_from('<I', img, 0x43854 + 4 * k)[0] - 0x8c2d0000) for k in range(1, 1271)]
print('ptr table: max len', max(len(x) for x in tl), collections.Counter(len(x) for x in tl).most_common(5))
print([x for x in tl if len(x) >= 12][:30])
print('with dot:', [x for x in tl if '.' in x][:40], sum(1 for x in tl if '.' in x))
