"""Build test discs for the dynamic experiments of docs/capacity-design.md (section 7).  Writes ONLY under build/.

  python -I -X utf8 tools/re/capacity/synth/mkdisc.py forceid [--name N] [--sources FLOW_PRG/CLUBEDIT.BIN ...]
        every pool of the listed overlays is rewritten (textrepack force=True) with NO translation: the game must
        behave exactly like the original (tests that no hidden pointer / relative reference to a string exists).
  python -I -X utf8 tools/re/capacity/synth/mkdisc.py synth SCALE [--name N] [--only SUBSTR ...] [--share none|dup]
                                                                  [--repack on|off] [--keep-tdb]
        every overlay record (optionally only sources containing SUBSTR) gets READABLE synthetic English whose length follows
        the measured per-category EN/JP distribution x SCALE (same model as joint.py), the real pipeline builds the patch.
        SCALE 0.85 ~ 'edited' English, 1.0 = natural English (many strings will not fit and stay Japanese).
  The result is build/out/<name>.gdi/.cue + track files (open the .gdi in Flycast).
"""
import sys, os, json, glob, hashlib, importlib.util, argparse
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('joint', os.path.join(here, 'joint.py'))
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)       # chdir to repo root, tools/ on sys.path
import build_patch as BP
import textdb as T, textrepack as R
import discbuild as D

WORDS = ('the club manager signs a young striker from the youth team and trains him hard for the next league match this '
         'season while the fans cheer at the stadium and the coach talks about tactics defence midfield attack and '
         'a new contract for the captain who wants to stay with the team').split()


def readable(raw, n, ja):
    """readable English of exactly n bytes, same number of lines as the Japanese (<= 39 chars per line)."""
    lines = ja.split('\n')
    k = len(lines)
    h = hashlib.blake2b(raw, digest_size=8).digest()
    seed = int.from_bytes(h, 'little')
    wt = [max(1, len(T.encode_text(x))) for x in lines]
    budget = n - (k - 1)
    if budget < k:                       # too short for k lines: one line
        lines, k, wt, budget = [ja], 1, [1], n
    out = []
    tot = sum(wt)
    for i in range(k):
        L = max(1, min(39, budget * wt[i] // tot)) if i < k - 1 else max(1, min(39, budget - sum(len(x) for x in out)))
        s = ''
        while len(s) < L:
            seed = (seed * 6364136223846793005 + 1442695040888963407) & (2 ** 64 - 1)
            s += (' ' if s else '') + WORDS[(seed >> 33) % len(WORDS)]
        out.append(s[:L].rstrip() or 'x')
    t = '\n'.join(out)
    if len(t) > n:
        t = t[:n]
    while len(t) < n:
        t += 'x'
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['forceid', 'synth'])
    ap.add_argument('scale', nargs='?', type=float, default=0.85)
    ap.add_argument('--name')
    ap.add_argument('--sources', nargs='*', default=['FLOW_PRG/CLUBEDIT.BIN', 'FLOW_PRG/MEETING.BIN', 'FLOW_PRG/NEWS.BIN',
                                                      'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/TRAINING.BIN', 'FLOW_PRG/HELP.BIN'])
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--share', default='none', choices=['none', 'dup'])
    ap.add_argument('--repack', default='on', choices=['on', 'off'])
    a = ap.parse_args()
    out_dir = os.path.join(BP.ROOT, 'build', 'out')
    if a.mode == 'forceid':
        patches = {}
        for src in a.sources:
            img = T.load_image(src)
            ex = T.extract_image(img)
            new, rp = R.repack(img.data, img.base, [], source=src, force=True, extracted=ex)
            bad = R.check(img.data, new, img.base, ex[0], {}, rp)
            assert not bad, bad
            n = sum(1 for x, y in zip(img.data, new) if x != y)
            print('%-24s %d pools rewritten, %d bytes differ from the original, self-check clean' % (src, rp.repacked_pools, n))
            if new != img.data:
                patches['/' + src] = new
                fp = os.path.join(BP.ROOT, 'build', 'forceid_files', src.replace('/', '_'))
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                open(fp, 'wb').write(new)      # for poolwrite.py DUMP SOURCE BASE IMAGEFILE
        name = a.name or 'forceid'
    else:
        emp = J.emp_ratios()
        tdb = os.path.join(BP.ROOT, 'build', 'synth_readable')
        os.makedirs(tdb, exist_ok=True)
        for f in glob.glob(os.path.join(tdb, '*.jsonl')):
            os.remove(f)
        for p in sorted(glob.glob(os.path.join(BP.ROOT, 'translation', '*.jsonl'))):
            nm = os.path.basename(p)
            if not nm.startswith(('FLOW_PRG__', 'ATFIRST__')):
                continue
            src = nm[:-6].replace('__', '/')
            if a.only and not any(o in src for o in a.only):
                continue
            with open(p, encoding='utf8') as f, open(os.path.join(tdb, nm), 'w', encoding='utf8', newline='\n') as g:
                for line in f:
                    r = json.loads(line)
                    raw = T.encode_text(r['ja'])
                    cat = J.RC.category(dict(r, file=nm[:-6]))
                    fct = J.quant(emp[cat], J.uhash(raw)) * a.scale
                    n = max(1, int(round(fct * (len(raw) + 1))) - 1)
                    r['en'] = readable(raw, n, r['ja'])
                    g.write(json.dumps(r, ensure_ascii=False) + '\n')
        res = BP.build_patches(tdb, repack=(a.repack == 'on'), share=a.share)
        BP.print_summary(res)
        patches = res.patches
        name = a.name or 'synth%02d%s' % (int(a.scale * 100), a.share)
    disc = D.build_disc(patches, out_dir, name, BP.ROOT)
    print('disc %s: %d files patched, end LBA %d -> %d' % (name, len(patches), disc['orig_end_lba'], disc['new_end_lba']))
    print('open', os.path.join(out_dir, name + '.gdi'))


if __name__ == '__main__':
    main()
