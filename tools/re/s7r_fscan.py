"""s7r_fscan FILE v1 v2 ... : offsets where all float32 LE values (given as pixel/512 numerators, i.e. v/512) appear within 64 bytes"""
import sys, struct
d = open(sys.argv[1], 'rb').read()
vals = [struct.pack('<f', int(v) / 512.0) for v in sys.argv[2:]]
hits = []
o = d.find(vals[0])
while o >= 0:
    win = d[max(0, o - 32):o + 64]
    if all(v in win for v in vals):
        hits.append(o)
    o = d.find(vals[0], o + 1)
print(len(hits), [hex(h) for h in hits[:20]])
