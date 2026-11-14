"""Find live tsString window objects in the RAM dumps by their sprite-template copy (obj+0x6c: full 24x24 template,
obj+0x80: half 12x24 template, both 'w,h,0,0,0,0,u1,v1' halfwords) and print obj fields (+0x3c cells, +0x3d rows, +0x3e advance, +0x3f lineh, +0x46 size class, +0x4a/+0x4c origin, +0x22 ncodes)."""
import os
import struct, sys, collections
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')) + '/build/emu/'
pat_full = struct.pack('<10H', 24, 24, 0, 0, 0, 0, 191, 191, 0, 0)[:16]
pat_half = struct.pack('<8H', 12, 24, 0, 0, 0, 0, 95, 191)
for name in sys.argv[1:] or ['ram_2400.bin', 'live1_ram.bin', 'live3_ram.bin', 't1_ram.bin']:
    d = open(R + name, 'rb').read()
    res = []
    i = d.find(pat_full)
    while i >= 0:
        # half template follows 0x14 later (desc entry stride 0x14)
        if d[i + 0x14:i + 0x14 + 16] == pat_half:
            o = i - 0x6c
            if o >= 0:
                g = lambda off, f='B': struct.unpack_from('<' + f, d, o + off)[0]
                res.append((0x8c000000 + o, g(0x3c), g(0x3d), g(0x3e), g(0x3f), g(0x46), g(0x4a, 'h'), g(0x4c, 'h'), g(0x22, 'H'), g(0x20)))
        i = d.find(pat_full, i + 1)
    print(name, len(res), 'live windows')
    adv = collections.Counter((r[3], r[1]) for r in res)
    for r in res[:60]:
        print('  obj %08x cells=%d rows=%d adv=%d lineh=%d size=%d x=%d y=%d ncodes=%d state=%d' % r)
