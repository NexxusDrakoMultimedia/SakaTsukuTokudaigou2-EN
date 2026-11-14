"""s8b: cut the still-untranslated BCAST commentary lines (distinct ja, frozen numbering of build/tx5/distinct.tsv) into per-speaker batches
for the stage-8 translation run.

    python -I -X utf8 tools/re/s8b_batches.py make [SIZE=100]   write build/tx5/s8/cNNN.txt  (N<TAB>ja<TAB>context) + build/tx5/s8/index.tsv
    python -I -X utf8 tools/re/s8b_batches.py status              count lines still without English, per batch (reads the jsonl + build/tx5/s8/res/*.tsv)

A line is "still untranslated" when no record with that ja has English in translation/BCAST__BCAST.BIN.jsonl and no results file of the
older runs (build/tx5/results/*.tsv, keyed by N) covers it.  Batches are single-speaker (kk Kimura, mm Miyazawa, mt Mizunuma, yh announcer)
and sorted by the clip category so a batch is one situation (replay intros, set pieces, season reviews ...).  The numbering N is the frozen
one of distinct.tsv, so results `N<TAB>en` merge with tools/re/tx5_merge.py exactly like the earlier runs.
"""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TX = os.path.join(ROOT, 'build', 'tx5')
S8 = os.path.join(TX, 's8')
JSONL = os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl')


def have_ja():
    have = set()
    for ln in open(JSONL, encoding='utf8'):
        r = json.loads(ln)
        if r.get('en'):
            have.add(r['ja'])
    return have


def done_numbers():
    done = set()
    for fp in glob.glob(os.path.join(TX, 'results', '*.tsv')) + glob.glob(os.path.join(S8, 'res', '*.tsv')):
        if os.path.basename(fp).startswith('names'):
            continue
        for ln in open(fp, encoding='utf8'):
            k = ln.split('\t', 1)[0]
            if k.isdigit():
                done.add(int(k))
    return done


def category(stem):
    s = stem.split('_', 1)[1] if '_' in stem else stem
    return re.sub(r'_?\d+[a-z]?(-\d*)?$', '', s)


def make(size):
    have = have_ja()
    done = done_numbers()
    groups = collections.defaultdict(list)
    for ln in open(os.path.join(TX, 'distinct.tsv'), encoding='utf8'):
        p = ln.rstrip('\n').split('\t')
        n = int(p[0])
        ja = p[2]
        stems = p[4].split()
        if n in done or ja in have or not stems:
            continue
        spk = stems[0].split('_', 1)[0]
        if spk == 'name':
            continue
        groups[spk].append((category(stems[0]), n, ja, ' '.join(stems[:3])))
    os.makedirs(S8, exist_ok=True)
    os.makedirs(os.path.join(S8, 'res'), exist_ok=True)
    idx = []
    k = 0
    for spk in ('kk', 'mm', 'mt', 'yh'):
        rows = sorted(groups.get(spk, []))
        for i in range(0, len(rows), size):
            k += 1
            chunk = rows[i:i + size]
            name = 'c%03d.txt' % k
            with open(os.path.join(S8, name), 'w', encoding='utf8', newline='\n') as f:
                for cat, n, ja, ex in chunk:
                    f.write('%d\t%s\t%s\n' % (n, ja, ex))
            idx.append((k, spk, len(chunk), chunk[0][0], chunk[-1][0]))
    with open(os.path.join(S8, 'index.tsv'), 'w', encoding='utf8', newline='\n') as f:
        for r in idx:
            f.write('%d\t%s\t%d\t%s\t%s\n' % r)
    tot = sum(r[2] for r in idx)
    print('batches', len(idx), 'lines', tot, dict(collections.Counter(r[1] for r in idx)))


def status():
    done = done_numbers()
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(S8, 'index.tsv'), encoding='utf8')]
    left = 0
    for k, spk, n, a, b in idx:
        rows = [l.split('\t')[0] for l in open(os.path.join(S8, 'c%03d.txt' % int(k)), encoding='utf8')]
        m = sum(1 for x in rows if int(x) not in done)
        left += m
        if m:
            print('c%03d %s %d/%d left' % (int(k), spk, m, len(rows)))
    print('lines left', left)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'make'
    if cmd == 'make':
        make(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    else:
        status()
