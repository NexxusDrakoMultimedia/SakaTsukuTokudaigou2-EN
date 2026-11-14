"""hwr_verify: independent read-back of a build's half-width pointer strings.

    python -I -X utf8 tools/re/hwr_verify.py DUMPDIR [TDBDIR]

DUMPDIR = build_patch --dump directory.  For every fmt=hwptr record with English in TDBDIR (default translation) every
pointer word that pointed at the record in the ORIGINAL overlay must now read the English (or, when the build refused the
string, still the Japanese).  Prints the counts; exit 1 on any mismatch.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import textdb as T            # noqa: E402
import textfmt_common as C    # noqa: E402
import textfmt_hwkana as H    # noqa: E402


def main(argv):
    dump = argv[0]
    tdb = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(TOOLS), 'translation')
    ok = ja_kept = bad = nfile = moved = 0
    for source, path in T.list_sources():
        jp = os.path.join(tdb, T.jsonl_name(source))
        if source == '1ST_READ.BIN' or not os.path.exists(jp):
            continue
        recs = [r for r in T.read_jsonl(jp) if r.get('fmt') == 'hwptr' and r.get('en')]
        if not recs:
            continue
        img = T.load_image(source)
        dp = os.path.join(dump, *source.split('/'))
        new = open(dp, 'rb').read() if os.path.exists(dp) else img.data
        words = H._words(img.data, img.base)
        allrecs = T.read_jsonl(jp)
        prot = sorted((int(r['id'].rsplit('#', 1)[1], 16), int(r['id'].rsplit('#', 1)[1], 16) + (r.get('max_bytes') or 0))
                      for r in allrecs if r.get('fmt') != 'hwptr')
        import bisect
        pst = [a for a, _ in prot]

        def protected(w):
            k = bisect.bisect_right(pst, w) - 1
            return k >= 0 and prot[k][0] <= w < prot[k][1]
        nfile += 1
        for r in recs:
            off = int(r['id'].rsplit('#', 1)[1], 16)
            en = C.encode_text(r['en'])
            ja = C.encode_text(r['ja'])
            ws = [w for w in words.get(off, []) if not protected(w)] if H.is_relocatable(r) else []
            if H.is_relocatable(r) and len(ws) != len(words.get(off, [])) and not ws:
                continue               # every word of this record sits inside text / a record array (cp932 bytes, not a pointer)
            if not ws:
                got = bytes(new[off:off + len(en) + 1])
                if got == en + b'\0':
                    ok += 1
                elif bytes(new[off:off + len(ja) + 1]) == ja + b'\0':
                    ja_kept += 1
                else:
                    bad += 1
                    print('BAD', r['id'])
                continue
            for w in ws:
                t = struct.unpack_from('<I', new, w)[0] - img.base
                s = bytes(new[t:new.index(b'\0', t) + 1])
                if s == en + b'\0':
                    ok += 1
                    moved += t != off
                elif s == ja + b'\0':
                    ja_kept += 1
                else:
                    bad += 1
                    print('BAD', r['id'], hex(w), s)
    print('verified %d overlays: %d pointers/strings read English (%d via a moved pointer), %d kept Japanese, %d BAD' % (
        nfile, ok, moved, ja_kept, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
