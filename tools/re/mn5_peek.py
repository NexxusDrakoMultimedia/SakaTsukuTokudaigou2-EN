"""mn5_peek.py REL OFF [N]: print N words at file offset OFF of an extracted overlay"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
d = MP.read_extracted(sys.argv[1]); off = int(sys.argv[2], 16); n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
print(len(d))
for k in range(n):
    print('%x: %08x' % (off + 4 * k, struct.unpack_from('<I', d, off + 4 * k)[0]))
