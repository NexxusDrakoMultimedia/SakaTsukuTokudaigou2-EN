import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
data = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
for pat in sys.argv[1:]:
    b = pat.encode()
    k = data.find(b)
    while k != -1:
        print(pat, hex(0x8c010000 + k), data[k:k+24])
        k = data.find(b, k + 1)
