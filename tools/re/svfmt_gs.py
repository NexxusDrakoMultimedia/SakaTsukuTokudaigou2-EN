"""svfmt_gs.py DUMP : first pointers of the game-state object gsp = *(0x8c159220) and which ones point into the 64KB save block 0x8ce4c000-0x8ce5c000."""
import sys, struct
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
gsp = w(0x8c159220); print('gsp', hex(gsp))
for o in range(0, 0x200, 4):
    v = w(gsp + o)
    tag = ''
    if 0x8ce4c000 <= v < 0x8ce5c000: tag = ' IN-SAVE-BLOCK +%x' % (v - 0x8ce4c000)
    elif 0x8c000000 <= v < 0x8d000000: tag = ' ram'
    if tag and 'IN-SAVE' in tag: print('gsp+%03x = %08x%s' % (o, v, tag))
print('ptr count into save block:', sum(1 for o in range(0, 0x1200, 4) if 0x8ce4c000 <= w(gsp + o) < 0x8ce5c000))
print('gsp+0x6c=%08x +0x84=%08x +0x34=%08x +0x3c=%08x' % (w(gsp+0x6c), w(gsp+0x84), w(gsp+0x34), w(gsp+0x3c)))
