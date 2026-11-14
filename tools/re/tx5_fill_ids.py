"""tx5: write English into existing records by id (id<TAB>en lines), for the few non-BCAST developer / debug strings of the match-engine
family and the other overlays (docs/uncovered-text.md section 'tx5 audit').

    python -I -X utf8 tools/re/tx5_fill_ids.py FILE.tsv [--write]

Only records whose en is empty and that carry no 'skip' flag are changed (money records stay with the money owner); the English must be
ASCII, may contain the original format codes (%d %s %x %f %02d <09>), and must fit max_bytes (len + 1 <= max_bytes).  A literal backslash-n
in the TSV is written as the newline escape the DB uses.  The jsonl lines are rewritten one by one in their original serialisation.
"""
import collections, glob, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def main():
    path = sys.argv[1]
    write = '--write' in sys.argv
    want = {}
    for ln in open(path, encoding='utf8'):
        if ln.strip():
            k, _, v = ln.rstrip('\n').partition('\t')
            want[k] = v.replace('\\n', '\n')
    done = collections.Counter()
    problems = []
    byfile = collections.defaultdict(list)
    for k in want:
        byfile[k.rsplit('#', 1)[0].replace('/', '__') + '.jsonl'].append(k)
    for fn, ids in sorted(byfile.items()):
        p = os.path.join(ROOT, 'translation', fn)
        if not os.path.exists(p):
            problems.append((ids[0], 'no such jsonl %s' % fn))
            continue
        out = []
        changed = 0
        with open(p, encoding='utf-8', newline='') as f:
            for line in f:
                body = line.rstrip('\r\n')
                eol = line[len(body):]
                if body.strip():
                    r = json.loads(body)
                    if r['id'] in want:
                        en = want[r['id']]
                        if r.get('en'):
                            problems.append((r['id'], 'already has English'))
                        elif r.get('skip'):
                            problems.append((r['id'], 'skip-flagged'))
                        elif not re.fullmatch(r"[\x20-\x7e\n]+", en.replace('<09>', '\t').replace('\t', '')):
                            problems.append((r['id'], 'non-ASCII'))
                        elif len(re.sub(r'<[0-9A-F]{2}>', 'x', en).encode('cp932')) + 1 > r['max_bytes']:
                            problems.append((r['id'], 'too long %d > %d' % (len(en) + 1, r['max_bytes'])))
                        else:
                            r['en'] = en
                            body = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
                            changed += 1
                            done[fn] += 1
                out.append(body + eol)
        if write and changed:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(''.join(out))
    print('records filled', sum(done.values()), 'in', len(done), 'files; problems', len(problems))
    for pr in problems[:30]:
        print('  ', *pr)
    print('(written)' if write else '(dry run)')


if __name__ == '__main__':
    main()
