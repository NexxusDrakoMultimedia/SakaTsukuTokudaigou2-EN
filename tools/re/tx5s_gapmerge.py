"""tx5 skeptic: add the fmt "gap" records (tools/textfmt_gap.py) with their English to translation/*.jsonl and set the English of the
tail records that continue a gap head.  Only these records are touched; every other line of the files is kept byte for byte.
    python -I -X utf8 tools/re/tx5s_gapmerge.py          (idempotent; reads tools/re/tx5s_gap_en.tsv and tx5s_gap_tails.tsv)"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textdb       # noqa: E402
import textfmt_gap  # noqa: E402


def tsv(name):
    d = {}
    for ln in open(os.path.join(HERE, name), encoding='utf8'):
        ln = ln.rstrip('\n')
        if ln:
            k, v = ln.split('\t', 1)
            d[k] = v.replace('\\n', '\n')
    return d


def main():
    en = tsv('tx5s_gap_en.tsv')
    tails = tsv('tx5s_gap_tails.tsv')
    done = 0
    for source in sorted(textfmt_gap.GAPS):
        data = open(os.path.join(ROOT, 'extracted', *source.split('/')), 'rb').read()
        new = textfmt_gap.extract(data, source)
        path = os.path.join(ROOT, 'translation', textdb.jsonl_name(source))
        lines = [ln for ln in open(path, encoding='utf8').read().split('\n') if ln]
        recs = [json.loads(ln) for ln in lines]
        have = {r['id']: r for r in recs}
        out = []
        for r in new:
            if r['id'] in have:
                have[r['id']]['en'] = en.get(r['id'], have[r['id']].get('en', ''))
                continue
            r['en'] = en.get(r['id'], '')
            have[r['id']] = r
            out.append(r)
        for rid, text in tails.items():
            if rid in have and rid.startswith(source + '#'):
                have[rid]['en'] = text
        allrecs = sorted(have.values(), key=textdb._off)
        textdb.write_jsonl(path, allrecs)
        done += len(out)
        print('%s: +%d gap records (%d total)' % (source, len(out), len(allrecs)))
    print('added', done)


if __name__ == '__main__':
    main()
