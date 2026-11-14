"""tx5: split the untranslated BCAST commentary lines (not the 'name' clips) into numbered batches for translation.

    python -I -X utf8 tools/re/tx5_batches.py make     freeze build/tx5/distinct.tsv  (N, tier, ja, count, example clips) and write
                                                        build/tx5/batches/bNNN.txt  (N<TAB>ja, 250 lines each, ordered by tier)
    python -I -X utf8 tools/re/tx5_batches.py status   how many distinct lines / records are translated, per tier

The numbering is FROZEN: `make` refuses to overwrite an existing distinct.tsv (--force to regenerate; results keyed by N then break).
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TX = os.path.join(ROOT, 'build', 'tx5')
JSONL = os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl')

# (tier, regex on the clip stem without the speaker prefix); the LOWEST tier a ja occurs in wins
TIERS = [
    (1, r'^(bgm|aisa|aidu|call|furi|koff|shoukai|siai_cha|scn_str|gm_leg|gm_pre|gm_tour|gm_name|uniform|end_aisa|end_match|end_time|end_furi|halfend|hkick|time_|new_team|stadi_kara|job|jiko)'),
    (2, r'^(pass|dri|shoot|sht|goal|foul|fk|ck|pk|gk|thrin|chan|replay|rplay|extime|pl_change|surp|chg|hftm|stadi)'),
    (3, r'^(end_|win|siame|siama|play|plan|tuika|setu|tm_|num_|gm_|zatu|oth|pks)'),
]


def stem_cat(stem):
    s = stem.split('_', 1)[1] if '_' in stem else stem
    return s


def tier_of(stem):
    s = stem_cat(stem)
    for t, rx in TIERS:
        if re.match(rx, s):
            return t
    return 4


def load():
    return [json.loads(l) for l in open(JSONL, encoding='utf8') if l.strip()]


def make(force=False):
    p = os.path.join(TX, 'distinct.tsv')
    if os.path.exists(p) and not force:
        print('distinct.tsv exists (frozen); use --force to rebuild')
        return
    recs = load()
    info = collections.OrderedDict()
    for r in recs:
        m = re.match(r'clip (\w+)\\(\S+) seg', r['ctx'])
        if not m or m.group(1) == 'name' or r.get('en'):
            continue
        d = info.setdefault(r['ja'], {'tier': 9, 'n': 0, 'ex': [], 'sp': set()})
        d['tier'] = min(d['tier'], tier_of(m.group(2)))
        d['n'] += 1
        d['sp'].add(m.group(1))
        if len(d['ex']) < 2:
            d['ex'].append(m.group(2))
    # order: tier, then speaker group (mt first: the other commentators are matched to it), then first occurrence
    order = sorted(info.items(), key=lambda kv: (kv[1]['tier'], 0 if 'mt' in kv[1]['sp'] or 'yh' in kv[1]['sp'] else 1, ))
    os.makedirs(os.path.join(TX, 'batches'), exist_ok=True)
    with open(p, 'w', encoding='utf8', newline='\n') as f:
        for i, (ja, d) in enumerate(order):
            f.write('%d\t%d\t%s\t%d\t%s\n' % (i, d['tier'], ja, d['n'], ' '.join(d['ex'])))
    per = 250
    for b in range(0, len(order), per):
        with open(os.path.join(TX, 'batches', 'b%03d.txt' % (b // per)), 'w', encoding='utf8', newline='\n') as f:
            for i in range(b, min(b + per, len(order))):
                ja, d = order[i]
                f.write('%d\t%s\n' % (i, ja))
    print('distinct', len(order), 'tiers', collections.Counter(d['tier'] for _, d in order))


def status():
    recs = load()
    n = collections.Counter()
    done = collections.Counter()
    ja_done = set()
    ja_all = {}
    for r in recs:
        m = re.match(r'clip (\w+)\\(\S+) seg', r['ctx'])
        folder = m.group(1)
        n[folder] += 1
        if r.get('en'):
            done[folder] += 1
        ja_all.setdefault(r['ja'], False)
        if r.get('en'):
            ja_all[r['ja']] = True
    for f in sorted(n):
        print('%-5s records %6d  with English %6d  (%.1f%%)' % (f, n[f], done[f], 100.0 * done[f] / n[f]))
    print('total records', len(recs), 'with English', sum(done.values()), 'distinct ja', len(ja_all), 'translated distinct', sum(ja_all.values()))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'make':
        make('--force' in sys.argv)
    elif len(sys.argv) > 1 and sys.argv[1] == 'status':
        status()
    else:
        print(__doc__)
