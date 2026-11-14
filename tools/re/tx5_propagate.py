"""tx5: reuse a finished English line for a Japanese line that differs from it only in punctuation, spacing, full/half-width forms or the
speech-style ending of the three commentators (ね / ねえ / ねぇ / よね / かな ...).

    python -I -X utf8 tools/re/tx5_propagate.py [--write]    -> build/tx5/results/r_prop.tsv  (<ja><TAB>en keyed by ja; merged by name 'names_*'?? no:
                                                               written as N<TAB>en against the frozen distinct list)
Only EXACT equality after normalisation is used (no fuzzy matching), so the English never describes different words.
"""
import collections, glob, json, os, re, sys, unicodedata
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
END = re.compile(r'(ですよね|ですかね|でしょうね|ですねえ|ですねぇ|ですね|ますね|ますよ|ですよ|ですな|でしょうか|ですか|ですが|でしょう|ねえ|ねぇ|ね|よね|かな|なあ|のう|よ|ぜ|か)+$')


def norm(s):
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'[、。，．,.!！?？…・\s「」『』（）()~〜ー\-―]+', '', s)
    s = re.sub(r'ぃ', 'い', s)
    s = END.sub('', s)
    return s


def main():
    recs = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8')]
    en_by_norm = collections.defaultdict(collections.Counter)
    for r in recs:
        if r.get('en') and not r['ctx'].startswith('clip name\\'):
            n = norm(r['ja'])
            if len(n) >= 4:
                en_by_norm[n][r['en']] += 1
    out = []
    seen = set()
    for ln in open(os.path.join(ROOT, 'build', 'tx5', 'distinct.tsv'), encoding='utf8'):
        p = ln.rstrip('\n').split('\t')
        ja = p[2]
        if ja in seen:
            continue
        n = norm(ja)
        if n in en_by_norm and len(n) >= 4:
            # skip if the Japanese itself already has English
            out.append((p[0], ja, en_by_norm[n].most_common(1)[0][0]))
            seen.add(ja)
    done = set()
    for r in recs:
        if r.get('en'):
            done.add(r['ja'])
    out = [o for o in out if o[1] not in done]
    print('propagation candidates', len(out))
    for n, ja, en in out[:25]:
        print('  ', ja, '=>', en)
    if '--write' in sys.argv:
        with open(os.path.join(ROOT, 'build', 'tx5', 'results', 'r_prop.tsv'), 'w', encoding='utf8', newline='\n') as f:
            for n, ja, en in out:
                f.write('%s\t%s\n' % (n, en))


if __name__ == '__main__':
    main()
