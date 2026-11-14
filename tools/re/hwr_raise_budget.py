"""hwr_raise_budget: raise `max_bytes` of the relocatable fmt=hwptr records to the per-record relocation budget.

    python -I -X utf8 tools/re/hwr_raise_budget.py [--budget 40] [--dry-run] [--revert] [FILE.jsonl ...]

Why (docs/hw-relocation.md): the extractor sets max_bytes to the in-place slot (4 / 8 / 12 bytes).  With
`build_patch.py --hw-relocate on` a pointer-referenced half-width string (club-name word, nation, league, foreign name part)
may be longer than its slot: it is moved into the free bytes of its overlay's pool.  The longest English the database
should accept for such a record is then a policy number (default 40 bytes incl. NUL), not the slot.  This tool writes that
number into `max_bytes` and keeps the physical slot in `slot` (right behind max_bytes), because the in-place writer
(textfmt_hwkana.apply, build_patch without the flag) must never use the budget as a slot width.

Touched: records with fmt == "hwptr", refs > 0, no "hwpool" in ctx (pointer-referenced) and max_bytes < budget.
Never touched: hwpool records (index-addressed, cannot move), recarr / text records, every other field, record order and ids.
Idempotent; --revert puts max_bytes back from `slot` and drops `slot`.  Each file is rewritten atomically (temp + os.replace)
and only when something changes; default files = translation/*.jsonl.
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import textdb as T            # noqa: E402
import textfmt_hwkana as H    # noqa: E402

DEFAULT_BUDGET = 40


def _raised(r, budget):
    out = {}
    for k, v in r.items():
        if k == 'slot':
            continue
        out[k] = v
        if k == 'max_bytes':
            out['slot'] = r.get('slot') or v
            out[k] = budget
    return out


def raise_file(path, budget=DEFAULT_BUDGET, write=True):
    """returns the number of records raised"""
    recs = T.read_jsonl(path)
    n = 0
    new = []
    for r in recs:
        if H.is_relocatable(r) and r['max_bytes'] < budget and not r.get('slot'):
            r = _raised(r, budget)
            n += 1
        new.append(r)
    if n and write:
        T.write_jsonl(path, new)
    return n


def revert_file(path, write=True):
    """returns the number of records restored"""
    recs = T.read_jsonl(path)
    n = 0
    new = []
    for r in recs:
        if r.get('fmt') == 'hwptr' and r.get('slot'):
            r = {k: (r['slot'] if k == 'max_bytes' else v) for k, v in r.items() if k != 'slot'}
            n += 1
        new.append(r)
    if n and write:
        T.write_jsonl(path, new)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*')
    ap.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--revert', action='store_true')
    a = ap.parse_args(argv)
    files = a.files or sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')))
    tot = nf = 0
    for p in files:
        n = revert_file(p, not a.dry_run) if a.revert else raise_file(p, a.budget, not a.dry_run)
        if n:
            nf += 1
            tot += n
            print('%s: %d records %s' % (os.path.basename(p), n, 'restored' if a.revert else 'raised to %d' % a.budget))
    print('%s %d records in %d files%s' % ('restored' if a.revert else 'raised', tot, nf, ' (dry run)' if a.dry_run else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
