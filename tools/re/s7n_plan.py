"""s7n plan: apply tools/re/s7n_rules.py to the DB records (dry run) and write the plan.

usage: s7n_plan.py plan.tsv            (writes plan.tsv: status, rule(s), id, max, ja, old en, new en; prints counts)
status: ok | grow | over_bytes (BCAST clip beyond its slot) | over_px | table (hwptr / recarr / hwpool / orphan record: not edited
here, forms.tsv + refit overlay); a record that does not change is not listed.
`classify(rec)` is shared with s7n_apply.py.  Nothing in translation/ is written here."""
import glob
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import s7n_rules as R  # noqa: E402
import pixelwidth as PW  # noqa: E402
import textfmt_common as C  # noqa: E402

NL = chr(10)


def window_cells(lines_px):
    return 33 if all(p <= 384 for p in lines_px) else 39


def bytes_of(en):
    return len(C.encode_text(en)) + 1


def rewrite(r):
    ja = R.norm_ja(r.get('ja') or '')
    new = r.get('en') or ''
    hits = []
    for name, jas, pats in R.RULES_C:
        if not any(j in ja for j in jas):
            continue
        for rx, rep in pats:
            n2 = rx.sub(rep, new)
            if n2 != new:
                new = n2
                hits.append(name)
    for name, ja_exact, crx, rep in R.CTX_RULES:
        if r.get('ja') == ja_exact and crx.search(r.get('ctx') or '') and new != rep:
            new = rep
            hits.append(name)
    return new, hits


def classify(r):
    """-> (status, new_en, hits) or None when the record does not change"""
    if not r.get('en'):
        return None
    new, hits = rewrite(r)
    if new == r['en']:
        return None
    fmt = r.get('fmt') or 'ptr'
    ctx = r.get('ctx') or ''
    mb0 = r.get('max_bytes')
    is_table = fmt in ('hwptr', 'recarr') or 'hwpool' in ctx or 'orphan' in ctx
    is_label = bool(mb0 and mb0 <= 40 and NL not in r['ja'] and len(r['ja']) <= 20 and '@' not in r['ja'] and '。' not in r['ja'] and not r['id'].startswith('BCAST/'))
    if is_table or is_label:
        # a label in a fixed slot / column: written here only when it fits the in-place slot without growing; else forms.tsv + overlay
        slot = r.get('slot') or mb0
        try:
            fits = bool(slot) and bytes_of(new) <= slot and bytes_of(new) <= bytes_of(r['en'])
        except Exception:  # noqa
            fits = False
        if not fits:
            return 'table', new, hits
    status = 'ok'
    mb = r.get('max_bytes')
    try:
        b = bytes_of(new)
        b0 = bytes_of(r['en'])
    except Exception:  # noqa
        b, b0 = 10 ** 6, 0
    if mb and b > mb and r['id'].startswith('BCAST/'):
        status = 'over_bytes'
    elif mb and b > max(mb, b0):
        status = 'grow'          # text record: the pool repack gives the room, the build proves it
    old_l = r['en'].split(NL)
    new_l = new.split(NL)
    wc = window_cells([PW.line_px(x)[0] for x in old_l])
    bad = [i for i, x in enumerate(new_l) if not PW.check_line(x, wc)['ok'] and PW.check_line(old_l[i] if i < len(old_l) else '', wc)['ok']]
    if bad and status in ('ok', 'grow'):
        status = 'over_px'
    return status, new, hits


def main():
    out = sys.argv[1]
    rows = []
    cnt = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        for ln in open(p, encoding='utf8'):
            if not ln.strip():
                continue
            r = json.loads(ln)
            res = classify(r)
            if not res:
                continue
            status, new, hits = res
            cnt[status] = cnt.get(status, 0) + 1
            rows.append((status, '+'.join(sorted(set(hits))), r['id'], str(r.get('max_bytes')), r['ja'].replace(NL, '\\n'), r['en'].replace(NL, '\\n'), new.replace(NL, '\\n')))
    with open(out, 'w', encoding='utf8', newline='\n') as fh:
        for row in sorted(rows):
            fh.write('\t'.join(row) + '\n')
    print(len(rows), 'planned', cnt)


if __name__ == '__main__':
    main()
