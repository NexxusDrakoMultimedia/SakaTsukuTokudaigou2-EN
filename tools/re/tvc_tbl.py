"""tvc_tbl.py FILE OFFHEX COUNT : u32 table dump."""
import sys, struct
d = open(sys.argv[1], 'rb').read()
o = int(sys.argv[2], 16)
for i in range(int(sys.argv[3])):
    print(i, struct.unpack_from('<I', d, o + 4 * i)[0])
