"""Self-test for tools/textdb.py.   python -I -X utf8 tools/test_textdb.py [--quick]

1. codec: decode/encode round-trips every extracted string byte-exact (all sources)
2. identity: extract -> records (through JSON text) -> insert with every 'en' empty
   reproduces every image byte-identical; the on-disc translation/*.jsonl files agree with a
   fresh extraction (id, ja, max_bytes, refs, orphan flag) = determinism
3. synthetic translations: N pseudo-random referenced strings of several images get ASCII
   text of assorted lengths; after insertion
     a) every pointer of every translated string resolves to its new text
     b) every other string and every other pointer is unchanged
     c) every changed byte lies inside the original region of a translated string, or is the
        pointer word of a translated (relocated) string, or lies in the appended area
   run with and without --append, and in 'safe' pad mode
4. stress: ALL referenced strings of MEETING.BIN translated at 1.0x and 1.3x JP byte length
"""
import json
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textdb as T  # noqa: E402

ROOT = T.ROOT
QUICK = '--quick' in sys.argv
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        if len(fails) < 40:
            print('FAIL:', msg)


def words(rng, n):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    out = []
    while sum(len(w) + 1 for w in out) < n:
        out.append(''.join(rng.choice(letters) for _ in range(rng.randint(2, 8))))
    t = ' '.join(out)[:n].rstrip()
    return t if t else 'x'


def load_all():
    srcs = []
    for source, path in T.list_sources():
        try:
            img = T.load_image(source, path)
        except ValueError:
            continue
        srcs.append((source, img, T.extract_image(img)))
    return srcs


def test_codec_and_identity(srcs):
    n_str = n_bytes = 0
    for source, img, (strs, ptrs, _) in srcs:
        for s in strs:
            check(T.encode_text(T.decode_text(s.raw)) == s.raw, 'codec %s#%x' % (source, s.off))
            n_str += 1
            n_bytes += len(s.raw)
        recs = T.build_records(img, strs, ptrs)
        recs = [json.loads(json.dumps(r, ensure_ascii=False)) for r in recs]
        new, rep = T.insert_image(img, recs, extracted=(strs, ptrs, None))
        check(new == img.data, 'identity %s' % source)
        check(rep.translated == 0, 'no translations expected %s' % source)
        jp = os.path.join(ROOT, 'translation', T.jsonl_name(source))
        if source == '1ST_READ.BIN':
            pass                      # jsonl for it is produced by another tool
        elif os.path.exists(jp):
            disk_all = T.read_jsonl(jp)
            disk = [r for r in disk_all if r.get('fmt') not in T.EXTRA_FMTS]      # hwptr / recarr: tools/textfmt_hwkana, textfmt_recarray
            same = len(disk) == len(recs) and all(
                a['id'] == b['id'] and a['ja'] == b['ja'] and a['max_bytes'] == b['max_bytes']
                and a['refs'] == b['refs'] and a.get('orphan') == b.get('orphan') for a, b in zip(disk, recs))
            check(same, 'jsonl on disc differs from fresh extraction: %s' % source)
            # the extra records (docs/uncovered-text.md) on disc agree with a fresh extraction too, never overlap a string
            # of the image and are in file order
            extra_disk = [r for r in disk_all if r.get('fmt') in T.EXTRA_FMTS]
            extra_new = T.extra_records(img, strs)
            # hwptr records whose max_bytes was raised to the relocation budget (tools/re/hwr_raise_budget.py) keep the
            # extracted slot in `slot`
            check([(r['id'], r['ja'], r.get('slot') or r['max_bytes'], r['fmt']) for r in extra_disk] ==
                  [(r['id'], r['ja'], r['max_bytes'], r['fmt']) for r in extra_new],
                  'extra records on disc differ from fresh extraction: %s' % source)
            import bisect
            core = sorted((s.off, s.off + s.max_bytes) for s in strs)
            core_starts = [a for a, _ in core]
            prev_end = -1
            for r in extra_new:
                a, b = T._off(r), T._off(r) + r['max_bytes']
                k = max(bisect.bisect_right(core_starts, a) - 1, 0)
                clash = False
                while k < len(core) and core[k][0] < b:
                    if core[k][1] > a:
                        clash = True
                    k += 1
                check(not clash and a >= prev_end, 'extra record %s overlaps another record' % r['id'])
                prev_end = b
        else:
            check(not recs, 'missing jsonl for %s' % source)
    print('codec+identity: %d images, %d strings, %d string bytes round-tripped' % (len(srcs), n_str, n_bytes))


def resolve(buf, base, wordoff):
    t = struct.unpack_from('<I', buf, wordoff)[0] - base
    return bytes(buf[t:buf.index(b'\0', t)])


def run_synthetic(source, img, ext, nsel, seed, append, pad_mode, mult=None):
    rng = random.Random(seed)
    if pad_mode != 'full':
        ext = T.extract_image(img, pad_mode=pad_mode)
    strs, ptrs, _ = ext
    cand = [s for s in strs if not s.orphan and s.refs]
    chosen = cand if nsel is None else rng.sample(cand, min(nsel, len(cand)))
    recs, want = [], {}
    for s in chosen:
        L = len(s.raw)
        ln = max(1, int(L * mult)) if mult else rng.choice([1, max(1, L // 2), max(1, L - 1), L, L + 1, L * 2, L * 4, 3])
        en = words(rng, ln)
        recs.append({'id': '%s#%x' % (source, s.off), 'ja': T.decode_text(s.raw), 'en': en})
        want[s.off] = T.encode_text(en)
    new, rep = T.insert_image(img, recs, append=append, pad_mode=pad_mode, extracted=ext)
    old = img.data
    failed_ids = {f[0] for f in rep.failed}
    allowed = bytearray(len(new))
    ptr_words = set()
    for s in strs:
        sid = '%s#%x' % (source, s.off)
        if s.off in want and sid not in failed_ids:
            for k in range(s.off, s.off + s.max_bytes):
                allowed[k] = 1
            for w in s.refs:
                got = resolve(new, img.base, w)
                check(got == want[s.off], 'ptr %s word %x -> %r expected %r' % (sid, w, got[:30], want[s.off][:30]))
                ptr_words.add(w)
        else:
            check(new[s.off:s.end + 1 + s.pad] == old[s.off:s.end + 1 + s.pad], 'untouched string changed %s' % sid)
            for w in s.refs:
                check(new[w:w + 4] == old[w:w + 4], 'untouched pointer changed %s' % sid)
    for w in ptr_words:
        allowed[w:w + 4] = b'\1\1\1\1'
    bad = [k for k in range(len(old)) if new[k] != old[k] and not allowed[k]]
    check(not bad, '%s: %d unexpected changed bytes, first at %#x' % (source, len(bad), bad[0] if bad else 0))
    if append:
        check(len(new) >= len(old) and (len(new) == len(old) or len(new) % 4 == 0), 'append size not 4-aligned')
        check(not [f for f in rep.failed if 'cannot be relocated' not in f[2]], 'append left failures')
    else:
        check(len(new) == len(old), 'image size changed without --append')
    print('  %-24s %-6s n=%-5d append=%-5s pad=%-4s %s' % (
        source, ('x%.1f' % mult) if mult else 'mixed', len(chosen), append, pad_mode, rep.line().split(': ', 1)[1]))


def main():
    t0 = time.time()
    srcs = load_all()
    print('extracted %d images in %.0fs' % (len(srcs), time.time() - t0))
    test_codec_and_identity(srcs)
    byname = {s: (i, e) for s, i, e in srcs}
    pick = ['FLOW_PRG/MEETING.BIN', 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/TRAINING.BIN', 'ATFIRST/HELP.BIN',
            '1ST_READ.BIN', 'FLOW_PRG/GAME.BIN']
    if QUICK:
        pick = pick[:2]
    print('synthetic:')
    for source in pick:
        img, ext = byname[source]
        for seed, append in ((1, False), (2, True)):
            if source == '1ST_READ.BIN' and append:
                continue
            run_synthetic(source, img, ext, 300, seed, append, 'full')
        run_synthetic(source, img, ext, 300, 3, False, 'safe')
    print('stress:')
    img, ext = byname['FLOW_PRG/MEETING.BIN']
    for mult in (1.0, 1.3):
        run_synthetic('FLOW_PRG/MEETING.BIN', img, ext, None, 5, False, 'full', mult=mult)
    print('done in %.0fs; %d failures' % (time.time() - t0, len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
