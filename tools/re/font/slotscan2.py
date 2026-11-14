"""Find mov.w @(d,PC),Rn loads of the font-slot offsets (0x3a8-0x3dc) in 1ST_READ and all overlays
(overlays reach the 1ST_READ jump table at 0x8c159000 via base register + mov.w offset)."""
import struct, csv, os, collections, sys
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
OFFS = {0x3a8:'font_init',0x3ac:'sjis2glyph',0x3b0:'byte2glyph_full',0x3b4:'glyph_blit_tex',0x3d0:'glyph_linear',0x3d8:'reverse_lookup',0x3b8:'?3b8',0x3bc:'?3bc',0x3c0:'?3c0',0x3c4:'?3c4',0x3c8:'?3c8',0x3cc:'?3cc',0x3d4:'?3d4',0x3dc:'?3dc'}
def scan(data, base):
    hits = []
    for o in range(0, len(data)-1, 2):
        w = struct.unpack_from('<H', data, o)[0]
        if w >> 12 == 9:
            ea = o + 4 + 2*(w & 0xff)
            if ea+2 <= len(data):
                v = struct.unpack_from('<H', data, ea)[0]
                if v in OFFS:
                    hits.append((base+o, v))
    return hits
def main():
    res = {}
    d = open(R+r'\extracted\1ST_READ.BIN','rb').read()
    res['1ST_READ'] = scan(d, 0x8c010000)
    for r in csv.DictReader(open(R+r'\build\memmap\overlays.tsv'), delimiter='\t'):
        if not r['base']: continue
        p = os.path.join(R,'extracted',r['dir'],r['overlay'])
        if not os.path.exists(p): continue
        res[r['overlay']] = scan(open(p,'rb').read(), int(r['base'],16))
    cnt = collections.Counter()
    for k,h in res.items():
        c = collections.Counter(v for _,v in h)
        for v in c: cnt[v]+=1
        print(k, {hex(v):n for v,n in sorted(c.items())})
    print('overlays per slot:', {hex(v):(OFFS[v],n) for v,n in sorted(cnt.items())})
main()
