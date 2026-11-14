"""uncovered: coverage audit of the translation database against the raw Japanese text on the disc.

Scans every file under extracted/ (and every decompressed container member under build/unpacked/, the
output of tools/unpack_all.py) for runs of Japanese text (cp932 kana / kanji / half-width katakana / full-width
symbols) and reports the runs NOT covered by any record of translation/*.jsonl.  A run is covered when at
least half of its bytes lie inside the byte range [offset, offset + len(ja) + 1) of a record whose id names the
same file (ids are '<source path>#<hex offset>', source = path below extracted/; records of members are
not part of the database, so members are always uncovered).

Run (never writes under extracted/):
    python -I -X utf8 tools/uncovered.py [--members build/unpacked] [--out build/uncovered]
                                         [--tdb DIR] [--no-members] [--only SUBSTR ...] [--min-chars N] [--top N]
Outputs in --out:  summary.tsv (one row per file/class), runs.tsv (every uncovered run: file, offset, class,
byte length, text), audit.md (ranked human readable tables).

Run classes (what the bytes look like, not where they come from):
    hw      half-width katakana only (+ ASCII punctuation), >= 3 hw chars        e.g. ﾐｭｰﾄｽ  (club-name pools)
    name    'Family Given' shape: 1-6 chars, one space, 1-8 chars                e.g. 織田 道三 (person records)
    kana    contains hiragana / katakana                                         prose, labels
    kanji   no kana, >= 2 kanji (town / person names, labels)
    kana* / kanji*   the same but NOT preceded by a NUL (record fields behind a non-zero stat byte)
A run must be NUL-terminated (or the end of the file) and either NUL-preceded or name-shaped, which is what
fixed-record tables look like (names preceded by a non-zero stat byte are found through the name shape).
Known limits: text that is split by control codes, text in compressed streams that unpack_all does not
open, and text stored in a non-cp932 encoding are not seen.  High-entropy files (zlib ratio > 0.93 on a sample)
are skipped and listed under 'skipped'.
"""
import argparse
import collections
import json
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import textfmt_common as C  # noqa: E402

EXTRACTED = os.path.join(ROOT, 'extracted')
TDB = os.path.join(ROOT, 'translation')

DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
CH = rb'(?:' + DB + rb'|[\x20-\x7e]|[\xa1-\xdf])'
STRICT = re.compile(rb'(?<![^\x00])(' + CH + rb'{2,})(?=\x00|\Z)')
HWCH = rb'(?:[\xa1-\xdf]|[ \x2d\x2e\x41-\x5a])'
NAMECH = rb'(?:' + DB + rb'|[\xa1-\xdf])'
NAME = re.compile(rb'(?<![\x81-\x9f\xe0-\xea])(' + NAMECH + rb'{1,6} ' + NAMECH + rb'{1,8})(?=\x00)')
LOOSE = re.compile(rb'(?<![\x81-\x9f\xe0-\xfc])((?:' + DB + rb'){2,})(?=\x00)')
HWSTR = re.compile('^[｡-ﾟ][｡-ﾟA-Za-z .-]{2,23}$')
HWREP = re.compile(r'(.)\1\1')
KANA = re.compile('[\u3041-\u30ff\uff66-\uff9f]')
KANJI = re.compile('[\u4e00-\u9fff]')
HWK = re.compile('[\uff66-\uff9f]')
FULLNONASC = re.compile('[\u3041-\u30ff\u4e00-\u9fff\uff00-\uff65\u3000-\u303f\u2000-\u27ff]')

SOURCE_ALIAS = {'ATFIRST/BPINFO.BIN': 'ETC_DATA/BPINFO.BIN'}      # one DB serves both copies (identical name fields)
SKIP_DIRS = ('SOUND/', 'SSONG/', 'DPSS/', 'BCAST/')
SKIP_NAMES = {'_filelist.tsv', '_manifest.tsv'}
SKIP_EXT = ('.GIF', '.WAV', '.PVR', '.MLT', '.DRV')

# visibility weight of a place (higher = the player meets it sooner / more often); see docs/uncovered-text.md
VIS = [
    (re.compile(r'^(FLOW_PRG/(TITLE|OPTION|S_SELECT|N_ENTRY|HEREWEGO|INITCON|CLUBEDIT|NEW_YEAR|CAP_SLCT|NEWUNIF|PLNUMSET|PL_EDIT|SEARCH|SPF_READ|SCDRF)\.BIN)'), 10),
    (re.compile(r'^FLOW_PRG/(GAME|OFFICE|ESTABLIS|GETREP|NENREP|HOMETOWN|SPONSOR2?|DRAFT|NEWCON|RECON|FIRE|YOUTH|ABROAD|WEEKLY|TOWN|TOWNDATA|SUPPORT|SPT_CLUB|LOCAL|INVEST)\.BIN'), 9),
    (re.compile(r'^FLOW_PRG/(EVENT|TV_EVENT|JSCEVENT|SELNAT|ENDING|MEETING|NEWS|NEWS_OP|NEWS_ED|TRAINING)\.BIN'), 9),
    (re.compile(r'^(1ST_READ\.BIN|ATFIRST/(TITLE|HELP)\.BIN|FLOW_PRG/HELP\.BIN)'), 8),
    (re.compile(r'^(ETC_DATA/BPINFO|ATFIRST/BPINFO)'), 8),
    (re.compile(r'^FLOW_PRG/(BPMATCH|BPMWEEK|CHALMODE|CHALDANI|CE_VS|SCHE[01]|ENDOPT|COMM|CON_REP|G_INCOME|G_RESULT|NF_CON|PASS_PL|J1_REP|PL_CON|LOAD|EXFLAG|BACKUP|AUTOSAVE|CSAVE3?4?|SONGSAVE|VTRLOAD|FREELOAD|EXTRADE)\.BIN'), 7),
    (re.compile(r'^FLOW_PRG/'), 5),
    (re.compile(r'^(2_DP\.BIN|DPETC/|DPWWW/)'), 1),
]


def vis_weight(path):
    for rx, w in VIS:
        if rx.match(path):
            return w
    return 3


def load_covered(tdb=None):
    """{source: sorted [(start, end)]} from translation/*.jsonl"""
    cov = collections.defaultdict(list)
    n = 0
    tdb = tdb or TDB
    for fn in sorted(os.listdir(tdb)):
        if not fn.endswith('.jsonl'):
            continue
        with open(os.path.join(tdb, fn), encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                src, _, off = r['id'].rpartition('#')
                try:
                    o = int(off, 16)
                except ValueError:
                    continue
                try:
                    ln = len(C.encode_text(r['ja']))
                except Exception:
                    ln = len(r['ja'])
                cov[src].append((o, o + ln + 1))
                n += 1
    for k in cov:
        cov[k].sort()
    return cov, n


def covered_fraction(iv, a, b):
    """fraction of [a, b) inside the (sorted) intervals iv"""
    import bisect
    if not iv:
        return 0.0
    i = bisect.bisect_right(iv, (a, 1 << 60)) - 1
    got = 0
    i = max(i, 0)
    while i < len(iv) and iv[i][0] < b:
        lo, hi = max(a, iv[i][0]), min(b, iv[i][1])
        if hi > lo:
            got += hi - lo
        i += 1
    return got / float(b - a)


def high_entropy(d):
    if len(d) < 4096:
        return False
    s = d[len(d) // 2:len(d) // 2 + 65536] if len(d) > 131072 else d
    return len(zlib.compress(s, 1)) > 0.93 * len(s)


def classify(b, s, off=0):
    """-> class name or None.  b = bytes, s = decoded str"""
    hw = len(HWK.findall(s))
    kana = len(KANA.findall(s)) - hw
    kanji = len(KANJI.findall(s))
    nonasc = sum(1 for c in s if ord(c) > 0x7f)
    if nonasc < 2 or nonasc * 2 < len(s):
        return None
    if hw >= 3 and kana == 0 and kanji == 0:
        return 'hw' if HWSTR.match(s) and not HWREP.search(s) and off % 4 == 0 else None
    if kana:
        return 'kana' if (kana >= 2 or kana + kanji >= 3) else None
    if kanji >= 2:
        # kanji-only text (towns, people, labels): no ASCII inside, mostly common (JIS level 1) kanji, else it is code / data
        if any(ord(c) < 0x80 for c in s.strip()) or len(s.strip()) < 2 or _level1(s) < 0.7:
            return None
        return 'kanji'
    return None


def _level1(s):
    k = l1 = 0
    for ch in s:
        if '一' <= ch <= '鿿':
            k += 1
            try:
                b = ch.encode('cp932')
            except Exception:
                continue
            if len(b) == 2 and (0x88 <= b[0] <= 0x97 or (b[0] == 0x98 and b[1] <= 0x72)):
                l1 += 1
    return 1.0 if not k else l1 / float(k)


def scan(d, min_chars):
    """-> [(offset, nbytes, class, text)] ; non-overlapping, ascending"""
    out = {}
    for m in STRICT.finditer(d):
        b = m.group(1)
        try:
            s = b.decode('cp932')
        except Exception:
            continue
        c = classify(b, s, m.start(1))
        if c and len(s) >= min_chars:
            out[m.start(1)] = (m.start(1), len(b), c, s)
    for m in NAME.finditer(d):
        b = m.group(1)
        o = m.start(1)
        if o in out:
            continue
        try:
            s = b.decode('cp932')
        except Exception:
            continue
        if sum(1 for ch in s if ord(ch) > 0x7f) < 3:
            continue
        # not already inside a strict run that contains it
        out[o] = (o, len(b), 'name', s)
    for m in LOOSE.finditer(d):
        o = m.start(1)
        if o in out or (o and d[o - 1] == 0):
            continue
        try:
            s = m.group(1).decode('cp932')
        except Exception:
            continue
        c = classify(m.group(1), s)
        if c in ('kana', 'kanji') and len(s) >= min_chars:
            out[o] = (o, len(m.group(1)), c + '*', s)
    runs = []
    last_end = -1
    for o in sorted(out):
        r = out[o]
        if r[0] < last_end:
            continue
        runs.append(r)
        last_end = r[0] + r[1]
    return runs


def iter_files(members_dir, no_members, only):
    manifest = set()
    mpath = os.path.join(members_dir, '_manifest.tsv')
    if os.path.exists(mpath) and not no_members:
        with open(mpath, encoding='utf-8') as f:
            next(f, None)
            for line in f:
                p = line.split('\t', 1)[0]
                if '/@' not in p:          # a container at offset 0 is replaced by its members; an overlay with embedded
                    manifest.add(p)        # members (FLOW_PRG/EVENT.BIN/@ebaf4/...) is still scanned itself
    for dp, dn, fn in os.walk(EXTRACTED):
        dn.sort()
        for f in sorted(fn):
            if f in SKIP_NAMES:
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, EXTRACTED).replace('\\', '/')
            if only and not any(o in rel for o in only):
                continue
            yield rel, full, rel in manifest
    if not no_members and os.path.isdir(members_dir):
        for dp, dn, fn in os.walk(members_dir):
            dn.sort()
            for f in sorted(fn):
                if f in SKIP_NAMES:
                    continue
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, members_dir).replace('\\', '/')
                if only and not any(o in rel for o in only):
                    continue
                yield rel, full, 'member'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tdb', help='translation database directory (default translation/)')
    ap.add_argument('--members', default=os.path.join('build', 'unpacked'))
    ap.add_argument('--out', default=os.path.join('build', 'uncovered'))
    ap.add_argument('--no-members', action='store_true')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--min-chars', type=int, default=2)
    ap.add_argument('--top', type=int, default=60)
    ap.add_argument('--keep-media', action='store_true', help='also scan SOUND/SSONG/DPSS and media extensions')
    a = ap.parse_args(argv)
    outdir = os.path.join(ROOT, a.out)
    os.makedirs(outdir, exist_ok=True)
    cov, nrec = load_covered(os.path.join(ROOT, a.tdb) if a.tdb else None)
    members_dir = os.path.join(ROOT, a.members)
    rows = {}          # (path, class) -> dict(n, chars, bytes, ex[])
    runs_f = open(os.path.join(outdir, 'runs.tsv'), 'w', encoding='utf-8', newline='\n')
    runs_f.write('file\toffset\tclass\tbytes\ttext\n')
    skipped = collections.Counter()
    skipped_files = collections.defaultdict(list)
    tot_runs = tot_cov = nfiles = 0
    for rel, full, kind in iter_files(members_dir, a.no_members, a.only):
        if kind is True:
            skipped['container (members scanned instead)'] += 1
            continue
        if not a.keep_media and kind != 'member' and (rel.startswith(SKIP_DIRS) or rel.upper().endswith(SKIP_EXT)):
            skipped['media (SOUND/SSONG/DPSS/BCAST, .GIF .WAV .PVR .MLT .DRV)'] += 1
            continue
        try:
            d = open(full, 'rb').read()
        except OSError:
            continue
        if high_entropy(d):
            skipped['high entropy (compressed / texture / audio)'] += 1
            skipped_files['high entropy'].append(rel)
            continue
        nfiles += 1
        src = rel if kind != 'member' else None
        src = SOURCE_ALIAS.get(src, src)
        iv = cov.get(src, []) if src else []
        for off, nb, cls, text in scan(d, a.min_chars):
            tot_runs += 1
            if iv and covered_fraction(iv, off, off + nb) >= 0.5:
                tot_cov += 1
                continue
            key = (rel, cls)
            r = rows.setdefault(key, dict(n=0, chars=0, bytes=0, ex=[]))
            r['n'] += 1
            r['chars'] += len(text)
            r['bytes'] += nb
            if len(r['ex']) < 6:
                r['ex'].append((off, text))
            runs_f.write('%s\t%x\t%s\t%d\t%s\n' % (rel, off, cls, nb, text.replace('\n', '\\n').replace('\t', ' ')))
    runs_f.close()
    with open(os.path.join(outdir, 'summary.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('file\tclass\truns\tchars\tbytes\tweight\texamples\n')
        for (rel, cls), r in sorted(rows.items(), key=lambda kv: (-vis_weight(kv[0][0]), -kv[1]['chars'], kv[0])):
            f.write('%s\t%s\t%d\t%d\t%d\t%d\t%s\n' % (rel, cls, r['n'], r['chars'], r['bytes'], vis_weight(rel),
                                                   ' | '.join('%x:%s' % e for e in r['ex'])))
    # ---- markdown
    tot_unc = sum(r['n'] for r in rows.values())
    md = []
    w = md.append
    w('# Coverage audit (tools/uncovered.py)\n')
    w('translation DB records: %d; files scanned: %d; Japanese runs found: %d, covered: %d, uncovered: %d\n' % (
        nrec, nfiles, tot_runs, tot_cov, tot_unc))
    w('skipped: ' + ', '.join('%s: %d' % kv for kv in sorted(skipped.items())) + '\n')
    by_class = collections.Counter()
    for (rel, cls), r in rows.items():
        by_class[cls] += r['n']
    w('uncovered by class: ' + ', '.join('%s %d' % kv for kv in by_class.most_common()) + '\n')
    w('## Files ranked by player visibility weight, then uncovered characters\n')
    w('| file | class | runs | chars | bytes | wt | examples |')
    w('|---|---|---:|---:|---:|---:|---|')
    ranked = sorted(rows.items(), key=lambda kv: (-vis_weight(kv[0][0]), -kv[1]['chars'], kv[0]))
    for (rel, cls), r in ranked[:a.top]:
        w('| %s | %s | %d | %d | %d | %d | %s |' % (rel, cls, r['n'], r['chars'], r['bytes'], vis_weight(rel),
                                              ' ; '.join('%x %s' % e for e in r['ex'][:3]).replace('|', '/')))
    with open(os.path.join(outdir, 'audit.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(md) + '\n')
    print('\n'.join(md[:5]))
    print('wrote', os.path.relpath(outdir, ROOT), '(summary.tsv, runs.tsv, audit.md)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
