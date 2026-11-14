"""s7t: read the stadium suffix and the changed unit rows back from a trial disc (read-only).
usage: s7t_readback.py DISC_DIR NAME   (DISC_DIR holds 'NAME (Track N).bin')"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gdrom
gdrom.BASE = sys.argv[2] + ' (Track %d).bin'
d = gdrom.Disc(sys.argv[1])
fs = {p: (l, s) for p, l, s in gdrom.walk(d, *gdrom.pvd_root(d))}
for src in ('/FLOW_PRG/SCHE0.BIN', '/FLOW_PRG/SCHE1.BIN'):
    l, s = fs[src]
    data = d.read(l, s)
    print(src, 'in-place suffix @0x39574:', data[0x39574:0x39580])
    for pat in (b'Trip %d man', b'%s Stadium'):
        print('   ', pat, [hex(i) for i in range(len(data)) if data.startswith(pat, i)][:4])
    print('   Japanese suffix left:', data.find('ｽﾀｼﾞｱﾑ'.encode('cp932')))
for src, pat in (('/FLOW_PRG/RECON.BIN', b'%d:%4d:%d man %d yr'), ('/FLOW_PRG/MEETING.BIN', b'Pay:%d00 man up:%d man'),
                 ('/FLOW_PRG/GETREP.BIN', b'Ratio: %d00 man / %d = %f'), ('/FLOW_PRG/SPT_CLUB.BIN', b'Ratio: %d00 man / %d = %f')):
    l, s = fs[src]
    data = d.read(l, s)
    print(src, pat, [hex(i) for i in range(len(data)) if data.startswith(pat, i)][:3])
