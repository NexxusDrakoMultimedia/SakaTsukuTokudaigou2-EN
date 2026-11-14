"""tx5: merge translation results into translation/BCAST__BCAST.BIN.jsonl.

    python -I -X utf8 tools/re/tx5_merge.py [--write] [--no-propagate]

Inputs (build/tx5/results/*.tsv, tab separated, one entry per line, '#' lines ignored):
  names.tsv            <record id> <en>                      (tx5_names.py)
  names_epithets.tsv   <ja> <en>                             applied to the records of the 'name' folder with that ja
  rNNN*.tsv            <N> <en>                              N = row of build/tx5/distinct.tsv (frozen); every record with that ja
Rules checked for every entry (a violation is reported and the entry is NOT merged):
  ASCII 0x20-0x7e only, no newline / '@' / '#' / '%' (message-engine markup), 1 <= len <= 73 for commentary (2 lines x 37 cells
  with the trailing space the builder adds), <= 15 for name clips; existing English is never overwritten (use --overwrite).
Propagation: the same Japanese text elsewhere in the file gets the same English (the parallel scripts of the three commentators).
"""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TX = os.path.join(ROOT, 'build', 'tx5')
JSONL = os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl')
MAX_COMM = 73
MAX_NAME = 15


def check(en, is_name):
    if not en:
        return 'empty'
    if not re.fullmatch(r"[\x20-\x7e]+", en):
        return 'non-ASCII or control character'
    if re.search(r'[@#%]', en):
        return 'markup character'
    lim = MAX_NAME if is_name else MAX_COMM
    if len(en) > lim:
        return 'too long (%d > %d)' % (len(en), lim)
    return None


def main():
    write = '--write' in sys.argv
    overwrite = '--overwrite' in sys.argv
    recs = [json.loads(l) for l in open(JSONL, encoding='utf8') if l.strip()]
    is_name = {r['id']: r['ctx'].startswith('clip name\\') for r in recs}
    by_ja = collections.defaultdict(list)
    for r in recs:
        by_ja[r['ja']].append(r)
    distinct = {}
    dp = os.path.join(TX, 'distinct.tsv')
    if os.path.exists(dp):
        for ln in open(dp, encoding='utf8'):
            p = ln.rstrip('\n').split('\t')
            distinct[int(p[0])] = p[2]
    byid = {r['id']: r for r in recs}
    bad = []
    pending = {}                     # record id -> en
    n_entries = 0
    for fp in sorted(glob.glob(os.path.join(TX, 'results', '*.tsv'))):
        base = os.path.basename(fp)
        for ln, line in enumerate(open(fp, encoding='utf8'), 1):
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            key, sep, en = line.partition('\t')
            if not sep:
                bad.append((base, ln, 'no tab'))
                continue
            n_entries += 1
            if base == 'names.tsv':
                targets = [byid[key]] if key in byid else []
            elif base.startswith('names_'):
                targets = [r for r in by_ja.get(key, []) if is_name[r['id']]]
            else:
                if not key.isdigit() or int(key) not in distinct:
                    bad.append((base, ln, 'unknown number %r' % key))
                    continue
                targets = [r for r in by_ja[distinct[int(key)]] if not is_name[r['id']]]
            if not targets:
                bad.append((base, ln, 'no record for %r' % key))
                continue
            why = check(en, is_name[targets[0]['id']])
            if why:
                bad.append((base, ln, '%s: %r' % (why, en)))
                continue
            for r in targets:
                if (r.get('en') and not overwrite) or r['id'] in pending and pending[r['id']] != en and not overwrite:
                    continue
                pending[r['id']] = en
    changed = 0
    for rid, en in pending.items():
        r = byid[rid]
        if r.get('en') != en:
            r['en'] = en
            changed += 1
    print('entries read', n_entries, 'problems', len(bad), 'records changed', changed, 'with English now',
          sum(1 for r in recs if r.get('en')), 'of', len(recs))
    for b in bad[:60]:
        print('  BAD %s:%d %s' % b)
    if len(bad) > 60:
        print('  ... %d more' % (len(bad) - 60))
    if write:
        tmp = JSONL + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
        os.replace(tmp, JSONL)
        print('wrote', JSONL)


if __name__ == '__main__':
    main()
