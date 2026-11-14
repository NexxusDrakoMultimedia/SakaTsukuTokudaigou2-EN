"""svfmt_bpid.py : find the BPINFO record (92 bytes, 64-byte header) whose bytes +0x0e.. equal the first runtime struct of the save arena (pt1 dump)
=> gives the player ID of struct 0 and whether the ID is stored in the 288-byte struct."""
import sys, glob, struct
f = glob.glob('extracted/**/BPINFO.BIN', recursive=True)[0]
b = open(f, 'rb').read()
d = open('build/emu/pt1_ram.bin', 'rb').read(); B = 0x8c000000
s0 = d[0x8ce4c004 - B:0x8ce4c004 - B + 0x5c]
for n in range(0, (len(b) - 64) // 92):
    r = b[64 + n * 92:64 + n * 92 + 92]
    if r[0x10:0x30] == s0[0x10:0x30]:
        print('record', n, 'matches struct0 bytes 0x10..0x30; name', r[:14]); break
else: print('no match')
print('count field', struct.unpack_from('<H', b, 0)[0], 'records', (len(b) - 64) // 92)
