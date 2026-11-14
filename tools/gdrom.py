"""GD-ROM (Redump bin/cue) ISO9660 reader/extractor for Dreamcast discs."""
import os, struct, sys
BASE = "Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan) (Track %d).bin"
SS = 2352
# (track file, absolute LBA of first sector in file)  -- high-density area begins at 45000
HD = [(3, 45000), (4, 45000+6342), (5, 45000+6342+5323)]
class Disc:
    def __init__(self, root="."):
        self.root = root
        self.tr = [(open(os.path.join(root, BASE % t), "rb"), lba, os.path.getsize(os.path.join(root, BASE % t))//SS, t) for t, lba in HD]
    def sector(self, lba):
        for f, s, n, t in self.tr:
            if s <= lba < s+n:
                f.seek((lba-s)*SS); return f.read(SS), t
        raise IndexError(lba)
    def read(self, lba, size):
        out = bytearray()
        while len(out) < size:
            raw, t = self.sector(lba)
            out += raw[16:16+2048]; lba += 1
        return bytes(out[:size])
def parse_dir(disc, lba, size):
    data = disc.read(lba, size); pos = 0; ents = []
    while pos < len(data):
        l = data[pos]
        if l == 0:
            pos = (pos//2048+1)*2048; continue
        elba, = struct.unpack_from("<I", data, pos+2); esz, = struct.unpack_from("<I", data, pos+10)
        flags = data[pos+25]; nl = data[pos+32]; name = data[pos+33:pos+33+nl]
        pos += l
        if name in (b"\x00", b"\x01"): continue
        ents.append((name.decode("ascii", "replace").split(";")[0], elba, esz, bool(flags & 2)))
    return ents
def walk(disc, lba, size, path=""):
    for name, elba, esz, isdir in parse_dir(disc, lba, size):
        p = path+"/"+name
        if isdir: yield from walk(disc, elba, esz, p)
        else: yield p, elba, esz
def pvd_root(disc):
    pvd = disc.read(45016, 2048)
    elba, = struct.unpack_from("<I", pvd, 156+2); esz, = struct.unpack_from("<I", pvd, 156+10)
    return elba, esz
if __name__ == "__main__":
    d = Disc(); r = pvd_root(d)
    print("root", r)
    for p, l, s in walk(d, *r): print("%10d %8d %s" % (s, l, p))
