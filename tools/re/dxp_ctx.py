"""Read-only: show u32 context around a value in a disc file (ISO path via extracted/). usage: dxp_ctx.py FILE VALUE [N]"""
import sys, struct
fn = sys.argv[1]; v = int(sys.argv[2], 0)
d = open('extracted/' + fn, 'rb').read()
n = len(d) // 4
w = struct.unpack('<%dI' % n, d[:n * 4])
k = 0
for i in range(n):
    if w[i] == v:
        print(fn, hex(i * 4), [hex(x) for x in w[max(0, i - 4):i + 5]])
        k += 1
        if k >= (int(sys.argv[3]) if len(sys.argv) > 3 else 5): break
