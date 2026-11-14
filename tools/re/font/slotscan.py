"""Scan 1ST_READ and all overlays for literal-pool references to the font jump-table slots."""
import struct, sys, os, csv, collections
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SLOTS = {0x8c1593a8:'font_init', 0x8c1593ac:'sjis2glyph', 0x8c1593b0:'byte2glyph(full)',
         0x8c1593b4:'glyph_blit(tex)', 0x8c1593d0:'glyph->linear', 0x8c1593d8:'reverse_lookup'}
def words(b):
    return struct.unpack('<%dI' % (len(b)//4), b[:len(b)//4*4])
def main():
    rows = list(csv.DictReader(open(R+r'\build\memmap\overlays.tsv'), delimiter='\t'))
    res = collections.defaultdict(dict)
    b = open(R+r'\extracted\1ST_READ.BIN','rb').read()
    w = words(b)
    for i,v in enumerate(w):
        if v in SLOTS: res['1ST_READ'].setdefault(SLOTS[v], []).append(hex(0x8c010000+i*4))
    for r in rows:
        p = os.path.join(R,'extracted',r['dir'],r['overlay'])
        if not os.path.exists(p) or not r['base']: continue
        b = open(p,'rb').read(); w = words(b); base=int(r['base'],16)
        for i,v in enumerate(w):
            if v in SLOTS: res[r['overlay']].setdefault(SLOTS[v], []).append(hex(base+i*4))
    for k,v in res.items():
        print(k, {a:len(c) for a,c in v.items()})
if __name__=='__main__': main()
