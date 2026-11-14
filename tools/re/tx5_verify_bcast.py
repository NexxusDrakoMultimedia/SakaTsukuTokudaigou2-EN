"""tx5: read BCAST.BIN of a BUILT trial disc and check it against translation/BCAST__BCAST.BIN.jsonl.

    python -I -X utf8 tools/re/tx5_verify_bcast.py build/trial NAME [--blank lead|trail]       (the folder that holds `NAME (Track N).bin`, NAME = the --name given to build_patch)

For every clip header: the magic, name, size and tag lines are byte-identical to the original; the segment table is ascending and
inside the sector; every segment holds the English of its record plus the builder's clip separator (build_patch.bcast_clip_text:
--blank lead = ONE leading blank in front of a clip that starts with a letter / digit / opening mark, the default and the standard build's
--clip-lead-space on; --blank trail = ONE trailing blank after every clip but the name callouts, --clip-lead-space off / --cell-prop off)
or, without English, the original Japanese; the audio sectors (every sector that is not a header) are byte-identical to the original disc
(sampled: every 97th, plus the sector behind each header).  Exit code 1 on any mismatch.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild            # noqa: E402
import textfmt_bcast as B   # noqa: E402
import textfmt_common as C  # noqa: E402


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    argv = list(sys.argv[1:])
    lead = True
    if '--blank' in argv:
        i = argv.index('--blank')
        if i + 1 >= len(argv) or argv[i + 1] not in ('lead', 'trail'):
            print('--blank needs lead or trail')
            return 2
        lead = argv[i + 1] == 'lead'
        del argv[i:i + 2]
    import build_patch as BP
    d = os.path.abspath(argv[0])
    name = argv[1] if len(argv) > 1 else os.path.basename(d)
    new = discbuild.Source(d, name)
    old = discbuild.Source(ROOT)
    recs = {}
    for ln in open(B.JSONL, encoding='utf8'):
        r = json.loads(ln)
        recs[int(r['id'].rsplit('#', 1)[1], 16)] = r
    pvd, rl, rs, rec = discbuild.read_filesystem(new)
    f = [r for r in rec if not r.isdir and r.path.upper() == '/BCAST/BCAST.BIN'][0]
    pvd0, rl0, rs0, rec0 = discbuild.read_filesystem(old)
    f0 = [r for r in rec0 if not r.isdir and r.path.upper() == '/BCAST/BCAST.BIN'][0]
    errs = []
    if (f.lba, f.size) != (f0.lba, f0.size):
        errs.append('BCAST.BIN moved or resized: %r vs %r' % ((f.lba, f.size), (f0.lba, f0.size)))
    nsec = (f.size + 2047) // 2048
    heads = 0
    en_seen = 0
    en_ok = 0
    relaid = 0
    audio_checked = 0
    for s in range(nsec):
        a = new.read(f.lba + s, 2048)
        if a[:16] == B.MAGIC:
            b = old.read(f0.lba + s, 2048)
            heads += 1
            if a[:0x60] != b[:0x60]:
                errs.append('header %d: name/size/tag lines changed' % s)
            if a[0x60:0x80] != b[0x60:0x80]:
                relaid += 1
            try:
                nm, segs = B.header_segments(a)
                nm0, segs0 = B.header_segments(b)
            except ValueError as e:
                errs.append('header %d: %s' % (s, e))
                continue
            if len(segs) != len(segs0):
                errs.append('header %d: segment count %d -> %d' % (s, len(segs0), len(segs)))
                continue
            for (o, slot, raw), (o0, slot0, raw0) in zip(segs, segs0):
                r = recs.get(s * 2048 + o0)
                if r is None:
                    if raw != raw0:
                        errs.append('header %d seg +%x changed without a record' % (s, o0))
                    continue
                if r.get('en'):
                    en_seen += 1
                    want = C.encode_text(BP.bcast_clip_text(r['en'], r['ctx'], lead))
                    if raw == want:
                        en_ok += 1
                    else:
                        errs.append('header %d seg +%x: %r != %r' % (s, o0, raw, want))
                elif raw != raw0:
                    errs.append('header %d seg +%x: no English but the bytes changed' % (s, o0))
        elif s % 97 == 0 or (s and new.read(f.lba + s - 1, 2048)[:16] == B.MAGIC):
            audio_checked += 1
            if a != old.read(f0.lba + s, 2048):
                errs.append('audio sector %d differs from the original' % s)
        if len(errs) > 20:
            break
    print('sectors', nsec, 'headers', heads, 'English segments seen', en_seen, 'ok', en_ok, 're-laid out clips', relaid,
          'audio sectors compared', audio_checked)
    for e in errs[:20]:
        print('  MISMATCH', e)
    print('RESULT', 'OK' if not errs else 'FAILED')
    new.close()
    old.close()
    return 0 if not errs else 1


if __name__ == '__main__':
    sys.exit(main())
