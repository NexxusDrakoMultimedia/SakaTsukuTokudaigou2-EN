"""Self-test of tools/zsarc_crc_audit.py (member_state / own_offsets on synthetic ZSARC members; the disc scan is run by hand, docs/helper-scripts.md):
python -I -X utf8 tools/test_zsarc_crc_audit.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bzlib                  # noqa: E402
import zsarc_crc_audit as Z   # noqa: E402

FAILS = []


def check(c, m):
    print(('ok   ' if c else 'FAIL ') + m)
    if not c:
        FAILS.append(m)


def main():
    plain = bytes(range(256)) * 8
    for meth in ('-nc--', '-bz--', '-bzw-'):
        blob = bzlib.pack_member('a.pvr', plain, meth)
        check(Z.member_state(blob, 0) == ('ok', 'a.pvr'), '%s: a fresh member is ok' % meth)
        m = bzlib.parse_member(blob, 0, with_data=False)
        t = bytearray(blob)
        t[m.data_offset + 5] ^= 0x55 if meth == '-nc--' else 0
        if meth == '-nc--':
            check(Z.member_state(bytes(t), 0)[0] == 'payload', '-nc--: a changed payload byte is STALE (payload CRC16)')
        t = bytearray(blob)
        t[11] ^= 0x01                                         # inside the orig_size field: header CRC (type-0 extension) no longer matches
        st = Z.member_state(bytes(t), 0)[0]
        check(st in ('hdrcrc', 'decode', 'payload'), '%s: a changed header field is caught (%s)' % (meth, st))
        t = bytearray(blob)
        t[:2] = b'\0\0'
        check(Z.member_state(bytes(t), 0)[0] == 'nohdr', '%s: no header at the offset' % meth)
    two = bzlib.pack_member('a', plain, '-nc--') + bzlib.pack_member('b', plain, '-bz--')
    check(Z.own_offsets(two) == [0, len(bzlib.pack_member('a', plain, '-nc--'))], 'own_offsets finds both members of a chain')
    print('ALL PASSED' if not FAILS else '%d FAILED' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
