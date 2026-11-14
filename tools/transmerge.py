"""transmerge: merge validated shard results into translation/*.jsonl, and report coverage.

    python -I -X utf8 tools/transmerge.py merge RESULT.json [RESULT.json ...] [options]
    python -I -X utf8 tools/transmerge.py status [--tdb DIR] [--shards DIR] [--json] [--all] [--pending]

merge
  * every result file is validated with transcheck against its shard (build/trans/shards/NNNN.json);
    items that fail are REFUSED (nothing of them is written) and listed in a repair work order
    build/trans/rejects/NNNN.json; the valid items of the same file are merged
    (--all-or-nothing: one failing item or malformed file refuses the whole run; --require-complete: missing items
    are failures)
  * a MALFORMED result file (unreadable, not JSON, top level not an object, "results" missing / null / not a list or map,
    bad "shard", shard file missing) is reported separately and skipped; the other files of the batch are still merged.
    A UTF-8 BOM is accepted.  Entries that are not objects with a string "key" are counted as BAD_ENTRY (not merged).
  * the English is written to EVERY record whose `ja` equals the item's `ja` (all ids of the distinct text);
    the fixed-slot budget is re-derived from the current database, so a stale shard cannot slip an overlong string in
  * an existing non-empty `en` is never replaced unless --overwrite (a different value is reported as a conflict);
    an empty result never blanks anything, so coverage can only grow; whitespace-only `en` is invalid for every item
  * skip-hinted items: empty en = nothing to do; en identical to ja = record gets "skip": true and en = ja
  * atomic: files are written to <name>.tmp and os.replace()d; only the lines that change are rewritten; stale
    *.jsonl.tmp files of a crashed run are removed
  * lock: a real merge takes build/trans/merge.lock (created with O_EXCL; --lock-file / --lock-timeout) around
    "load database -> write files", so two concurrent merges serialise and the second one re-reads the database after the
    first has written.  A lock file left behind by a crashed run cannot be detected by pid on every platform: after
    --lock-timeout seconds (default 60) the merge stops with a message naming the file; delete it if no merge is running.
  * backup: before the first write the previous version of every file that will change is copied to
    build/trans/backup/NNNN/ (NNNN = running counter) with a manifest.json
  * idempotent: merging the same results again changes nothing and creates no backup
  * prints coverage statistics afterwards (records with en, distinct texts translated, per category)
  * paths: every path argument (result files, --tdb, --shards, --shard-file, --backup-dir, --rejects-dir, --lock-file) is
    taken as given when absolute; a relative path is looked for in the CURRENT directory first, then under the repository
    root; a relative path that exists in neither place is created relative to the current directory.
Exit code: 0 = everything merged; 1 = some items refused or BAD_ENTRY entries (the valid ones are merged);
2 = a malformed / unreadable result file (the valid files of the batch ARE merged), the lock could not be taken,
or a usage / IO error.

status
  records / distinct texts translated, per source file, per category, and the shards that still have work
  (--pending prints just those shard numbers, one per line, for driving a translator fleet).
"""
import argparse
import collections
import contextlib
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translib as T      # noqa: E402
import transcheck as C    # noqa: E402
import transwork as W     # noqa: E402

LOCK_FILE = os.path.join(T.TRANS_DIR, 'merge.lock')
LOCK_TIMEOUT = 60.0


class LockTimeout(RuntimeError):
    pass


class MergeLock:
    """Cross-process mutex: a lock file created with O_CREAT|O_EXCL, removed on exit.  There is no pid-based stale
    detection (not portable), so a lock that is not released within `timeout` seconds raises LockTimeout with a
    message that names the file and says how to clear it."""

    def __init__(self, path, timeout=LOCK_TIMEOUT, poll=0.05):
        self.path = path
        self.timeout = float(timeout)
        self.poll = poll
        self.held = False

    def _describe(self):
        try:
            age = time.time() - os.path.getmtime(self.path)
            with open(self.path, encoding='utf-8', errors='replace') as fh:
                owner = fh.read().strip().replace('\n', ' ')
            return 'created %.0f s ago by %s' % (age, owner or 'an unknown process')
        except OSError:
            return 'owner unknown'

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except (FileExistsError, PermissionError):      # Windows: PermissionError while the holder is deleting it
                if time.monotonic() >= deadline:
                    raise LockTimeout(
                        'merge lock %s is still held after %g s (%s). Another transmerge is probably running: wait for it. '
                        'If no merge is running (a crashed run leaves the file behind), delete the lock file and run again; '
                        'use --lock-timeout to wait longer.' % (self.path, self.timeout, self._describe()))
                time.sleep(self.poll)
        try:
            os.write(fd, ('pid %d at %s\n' % (os.getpid(), time.strftime('%Y-%m-%d %H:%M:%S'))).encode('ascii'))
        finally:
            os.close(fd)
        self.held = True
        return self

    def __exit__(self, *exc):
        if self.held:
            self.held = False
            try:
                os.remove(self.path)
            except OSError:
                pass
        return False


def clean_stale_tmp(directory, suffix):
    """Remove `*<suffix>` temp files that a crashed atomic write left behind (the caller holds the merge lock)."""
    removed = []
    if directory and os.path.isdir(directory):
        for fn in sorted(os.listdir(directory)):
            if fn.endswith(suffix):
                try:
                    os.remove(os.path.join(directory, fn))
                    removed.append(fn)
                except OSError:
                    pass
    return removed


def ja_index(db):
    idx = collections.defaultdict(list)
    for fi, li, r in db.records():
        idx[r['ja']].append((fi, li))
    return idx


def db_fixed_budget(db, positions):
    """Smallest max_bytes among the records of one text that can only be written in place."""
    best = None
    for fi, li in positions:
        r = db.files[fi].recs[li]
        mb = r.get('max_bytes')
        if mb is not None and T.is_fixed(r) and (best is None or mb < best):
            best = mb
    return best


def _rel(p):
    try:
        return os.path.relpath(p, T.ROOT)
    except ValueError:                    # other drive
        return p


def count_en(db):
    return sum(1 for _, _, r in db.records() if r.get('en'))


class MergeReport:
    def __init__(self):
        self.filled = 0           # records that received an English string
        self.replaced = 0         # --overwrite replacements
        self.unchanged = 0        # records that already had exactly this string
        self.conflicts = []       # (id, existing, new)
        self.refused = []         # (shard, key, [codes])
        self.bad_entries = []     # (shard, result file, message): entries without a usable string "key"
        self.malformed = []       # (result file, reason): files that could not be used at all
        self.stale_tmp = []       # temp files of a crashed run that were removed
        self.skipped_empty = 0    # skip-hinted items left alone
        self.items_merged = 0
        self.files_changed = []
        self.backup = None
        self.rejects = []         # paths of repair files

    def changed(self):
        return self.filled + self.replaced


def merge(db, results, shards_dir=None, shard_file=None, overwrite=False, require_complete=False,
          all_or_nothing=False, extra_lines=0, dry_run=False, backup_root=None, rejects_dir=None, malformed=None):
    """results: list of (label, result dict).  Mutates db records in memory (and writes the changed files unless
    dry_run); returns (MergeReport, coverage_before).  A result that cannot be used (not shaped like a result file,
    bad shard number, shard file missing) is recorded in report.malformed and skipped, the others are merged;
    `malformed` = (label, reason) pairs of files the caller could not even load.  The caller holds the merge lock."""
    shards_dir = shards_dir or T.SHARD_DIR
    rep = MergeReport()
    rep.malformed = list(malformed or [])
    before = count_en(db)
    idx = ja_index(db)
    plans = []                      # (label, shard, check report, result)
    for label, result in results:
        try:
            shard = C.find_shard(shard_file, shards_dir, result)
            cr = C.check_result(shard, result, extra_lines, allow_missing=not require_complete)
        except (OSError, ValueError) as ex:          # MalformedInput is a ValueError
            rep.malformed.append((label, str(ex)))
            continue
        plans.append((label, shard, cr, result))
        for e in cr['errors']:
            if e['code'] == 'BAD_ENTRY' and e.get('key') is None:
                rep.bad_entries.append((shard.get('shard'), label, e['msg']))
    if all_or_nothing and (rep.malformed or any(not cr['ok'] for _, _, cr, _ in plans)):
        for label, shard, cr, _ in plans:
            for e in cr['errors']:
                if e.get('key') is not None:
                    rep.refused.append((shard.get('shard'), e.get('key'), [e['code']]))
        return rep, before

    changed_files = collections.OrderedDict()      # fi -> set(li)
    for label, shard, cr, result in plans:
        items = {it['key']: it for it in shard['items']}
        bad_keys = {}
        for e in cr['errors']:
            if e.get('key') is not None:
                bad_keys.setdefault(e['key'], []).append(e['code'])
        for key, codes in bad_keys.items():
            rep.refused.append((shard.get('shard'), key, codes))
        entries = {k: en for k, en, _ in C.result_entries(result) if k is not None}
        good = []
        for key in entries:
            if key in items and key not in bad_keys and cr['keys'].get(key, {}).get('ok'):
                good.append(key)
        extra_bad = {}
        for key in good:
            it = items[key]
            pos = idx.get(it['ja'])
            if not pos:
                extra_bad[key] = ['STALE']
                continue
            en = entries[key]
            if it.get('skip') and en == '':
                continue
            bf = db_fixed_budget(db, pos)
            if bf is not None and en != it['ja'] and len(en.encode('cp932', errors='replace')) + 1 > bf:
                extra_bad[key] = ['OVER_BUDGET']
        for key, codes in extra_bad.items():
            rep.refused.append((shard.get('shard'), key, codes))
            bad_keys[key] = codes
        for key in good:
            if key in bad_keys:
                continue
            it = items[key]
            en = entries[key]
            if it.get('skip') and en == '':
                rep.skipped_empty += 1
                continue
            identity = bool(it.get('skip')) and en == it['ja']
            rep.items_merged += 1
            for fi, li in idx[it['ja']]:
                r = db.files[fi].recs[li]
                old = r.get('en') or ''
                if old == en and (not identity or r.get('skip')):
                    rep.unchanged += 1
                    continue
                if old and old != en and not overwrite:
                    rep.conflicts.append((r['id'], old, en))
                    continue
                if old and old != en:
                    rep.replaced += 1
                else:
                    rep.filled += 1
                r['en'] = en
                if identity:
                    r['skip'] = True
                changed_files.setdefault(fi, set()).add(li)
        if bad_keys and rejects_dir is not None and not dry_run:
            # repair order for the refused items (checker errors + merge-level refusals)
            cr2 = dict(cr)
            cr2['errors'] = list(cr['errors']) + [
                {'key': k, 'code': c, 'ja': items[k]['ja'], 'en': C._safe(entries.get(k)), 'msg': 'refused at merge time (%s)' % c,
                 'hint': 'database changed since the shard was planned: re-run transwork.py plan' if c == 'STALE'
                 else 'shorten: the current database has a tighter fixed slot than the shard says'}
                for k, cs in extra_bad.items() for c in cs]
            os.makedirs(rejects_dir, exist_ok=True)
            p = os.path.join(rejects_dir, '%04d.json' % int(shard.get('shard') or 0))
            T.write_atomic(p, json.dumps(C.repair_file(shard, cr2), ensure_ascii=False, indent=1) + '\n')
            rep.rejects.append(p)
        elif not bad_keys and rejects_dir is not None and not dry_run:
            # a clean merge supersedes any earlier repair order for this shard
            old = os.path.join(rejects_dir, '%04d.json' % int(shard.get('shard') or 0))
            if os.path.exists(old):
                os.remove(old)

    after = count_en(db)
    if after < before:
        raise RuntimeError('merge would lower coverage (%d -> %d): refusing' % (before, after))
    if changed_files and not dry_run:
        for fi in changed_files:
            if not db.files[fi].plain:
                raise RuntimeError('%s has blank lines / CRLF / no final newline: refusing to rewrite it' % db.files[fi].name)
        backup_root = backup_root or T.BACKUP_DIR
        os.makedirs(backup_root, exist_ok=True)
        n = 1 + max([int(d) for d in os.listdir(backup_root) if d.isdigit()] or [0])
        bdir = os.path.join(backup_root, '%04d' % n)
        os.makedirs(bdir)
        for fi in changed_files:
            shutil.copy2(db.files[fi].path, os.path.join(bdir, os.path.basename(db.files[fi].path)))
        manifest = {'results': [p[0] for p in plans], 'files': [db.files[fi].name + '.jsonl' for fi in changed_files],
                    'records_changed': rep.changed(), 'coverage_before': before}
        T.write_atomic(os.path.join(bdir, 'manifest.json'), json.dumps(manifest, indent=1) + '\n')
        rep.backup = bdir
        for fi, lis in changed_files.items():
            f = db.files[fi]
            for li in lis:
                f.lines[li] = T.dump_record(f.recs[li], f.compact)
            T.normalise_styles(f)          # heal lines another writer left in the other separator style
            T.write_atomic(f.path, '\n'.join(f.lines) + '\n')
            rep.files_changed.append(f.name)
    else:
        rep.files_changed = [db.files[fi].name for fi in changed_files]
    return rep, before


# ----------------------------------------------------------------- status ----

def distinct_state(db):
    """-> {ja: (records, with_en)}"""
    st = {}
    for _, _, r in db.records():
        a = st.get(r['ja'])
        if a is None:
            a = st[r['ja']] = [0, 0]
        a[0] += 1
        if r.get('en'):
            a[1] += 1
    return st


def coverage(db, items=None, shards_dir=None):
    items = items if items is not None else W.build_items(db)
    st = distinct_state(db)
    cat = collections.OrderedDict((c, collections.Counter()) for c in W.CAT_ORDER)
    for it in items:
        recs, en = st[it['ja']]
        c = cat[it['_cat']]
        c['texts'] += 1
        c['records'] += recs
        c['records_en'] += en
        if it['skip']:
            c['skip'] += 1
            c['skip_done'] += 1 if en == recs else 0
        else:
            c['todo_texts'] += 1
            c['done'] += 1 if en == recs else 0
    src = collections.OrderedDict()
    for f in db.files:
        n = len(f.recs)
        e = sum(1 for r in f.recs if r.get('en'))
        src[f.name] = (n, e)
    out = {
        'records': db.count(), 'records_en': count_en(db), 'texts': len(items),
        'texts_done': sum(1 for it in items if st[it['ja']][1] == st[it['ja']][0]),
        'texts_partial': sum(1 for it in items if 0 < st[it['ja']][1] < st[it['ja']][0]),
        'skip_texts': sum(1 for it in items if it['skip']),
        'skip_texts_done': sum(1 for it in items if it['skip'] and st[it['ja']][1] == st[it['ja']][0]),
        'todo_texts': sum(1 for it in items if not it['skip']),
        'todo_done': sum(1 for it in items if not it['skip'] and st[it['ja']][1] == st[it['ja']][0]),
        'categories': {c: dict(v) for c, v in cat.items() if v['texts']},
        'sources': {k: {'records': n, 'with_en': e} for k, (n, e) in src.items()},
    }
    # shards that still have work
    pend, done, partial, unreadable = [], 0, 0, []
    shards_dir = shards_dir or T.SHARD_DIR
    if os.path.isdir(shards_dir):
        for fn in sorted(os.listdir(shards_dir)):
            if not fn.endswith('.json'):
                continue
            try:
                sh = C.load_shard(os.path.join(shards_dir, fn))
            except (OSError, ValueError):
                unreadable.append(fn)
                continue
            todo = [it for it in sh['items'] if not it.get('skip')
                    and (st.get(it['ja']) is None or st[it['ja']][1] != st[it['ja']][0])]
            nd = sum(1 for it in sh['items'] if not it.get('skip') and st.get(it['ja']) and st[it['ja']][1] == st[it['ja']][0])
            if todo:
                pend.append({'shard': sh['shard'], 'category': sh['category'], 'area': sh['area'], 'todo': len(todo),
                             'done': nd, 'items': len([i for i in sh['items'] if not i.get('skip')])})
                if nd:
                    partial += 1
            else:
                done += 1
        out['shards'] = {'complete': done, 'partial': partial, 'pending': len(pend), 'pending_list': pend,
                         'unreadable': unreadable}
    return out


def pct(a, b):
    return '%5.1f%%' % (100.0 * a / b) if b else '    - '


def format_status(cov, show_all=False):
    o = []
    o.append('records with en: %d / %d (%s)' % (cov['records_en'], cov['records'], pct(cov['records_en'], cov['records']).strip()))
    o.append('distinct texts: %d; translated %d (%s), partly %d; to do (no skip hint) %d of which done %d; skip-hinted %d (done %d)' % (
        cov['texts'], cov['texts_done'], pct(cov['texts_done'], cov['texts']).strip(), cov['texts_partial'],
        cov['todo_texts'], cov['todo_done'], cov['skip_texts'], cov['skip_texts_done']))
    if 'shards' in cov:
        s = cov['shards']
        o.append('shards: %d complete, %d with work left (%d of them started)' % (s['complete'], s['pending'], s['partial']))
        if s.get('unreadable'):
            o.append('WARNING: unreadable shard files (re-run transwork.py plan): ' + ', '.join(s['unreadable'][:10]))
    o.append('')
    o.append('%-10s %8s %8s %8s %9s %9s  %s' % ('category', 'texts', 'done', 'skip', 'records', 'rec en', 'coverage(todo)'))
    for c, v in cov['categories'].items():
        o.append('%-10s %8d %8d %8d %9d %9d  %s' % (c, v['texts'], v.get('done', 0), v.get('skip', 0), v['records'],
                                                   v.get('records_en', 0), pct(v.get('done', 0), v.get('todo_texts', 0))))
    o.append('')
    o.append('%-34s %8s %8s %8s' % ('source file', 'records', 'with en', 'cover'))
    shown = 0
    for k, v in cov['sources'].items():
        if show_all or v['with_en']:
            o.append('%-34s %8d %8d %s' % (k, v['records'], v['with_en'], pct(v['with_en'], v['records'])))
            shown += 1
    if not show_all:
        o.append('(%d source files without any English not shown; --all lists them)' % (len(cov['sources']) - shown))
    return '\n'.join(o)


def format_merge(rep, before, after, cov):
    o = []
    o.append('merged items: %d; records filled %d, replaced %d, already identical %d, conflicts %d, refused items %d, skip-hinted left alone %d' % (
        rep.items_merged, rep.filled, rep.replaced, rep.unchanged, len(rep.conflicts), len(rep.refused), rep.skipped_empty))
    if rep.malformed:
        o.append('MALFORMED result files (not merged, reported separately): %d' % len(rep.malformed))
        for label, why in rep.malformed[:40]:
            o.append('  MALFORMED %s: %s' % (C._safe(label), C._safe(why)))
    if rep.bad_entries:
        o.append('BAD_ENTRY: %d result entries without a usable string "key" (not merged)' % len(rep.bad_entries))
        for sh, label, msg in rep.bad_entries[:10]:
            o.append('  BAD_ENTRY shard %s in %s: %s' % (sh, C._safe(label), msg))
        if len(rep.bad_entries) > 10:
            o.append('  ... %d more BAD_ENTRY' % (len(rep.bad_entries) - 10))
    if rep.stale_tmp:
        o.append('removed stale temp files: ' + ', '.join(rep.stale_tmp))
    for sh, key, codes in rep.refused[:40]:
        o.append('  REFUSED shard %s key %s: %s' % (sh, C._safe(key), ','.join(sorted(set(codes)))))
    if len(rep.refused) > 40:
        o.append('  ... %d more refused' % (len(rep.refused) - 40))
    for rid, old, new in rep.conflicts[:10]:
        o.append('  CONFLICT %s keeps %r (new %r); use --overwrite to replace' % (rid, old[:40], new[:40]))
    if rep.backup:
        o.append('backup of the previous files: %s' % _rel(rep.backup))
    if rep.rejects:
        o.append('repair work orders: ' + ', '.join(_rel(p) for p in rep.rejects))
    o.append('files changed: %s' % (', '.join(rep.files_changed) if rep.files_changed else 'none'))
    o.append('coverage: records with en %d -> %d of %d (%s); distinct texts translated %d of %d (%s)' % (
        before, after, cov['records'], pct(after, cov['records']).strip(), cov['texts_done'], cov['texts'],
        pct(cov['texts_done'], cov['texts']).strip()))
    o.append('per category (done / to do): ' + ', '.join(
        '%s %d/%d' % (c, v.get('done', 0), v.get('todo_texts', 0)) for c, v in cov['categories'].items()))
    return '\n'.join(o)


def cmd_merge(a):
    if a.shard_file and len(a.results) != 1:
        print('transmerge: --shard-file needs exactly one result file', file=sys.stderr)
        return 2
    # one path rule for everything (translib.resolve_path): absolute as is, else current directory first, then repo root
    tdb = T.resolve_path(a.tdb)
    shards = T.resolve_path(a.shards)
    shard_file = T.resolve_path(a.shard_file) if a.shard_file else None
    backup_dir = T.resolve_path(a.backup_dir)
    rejects_dir = T.resolve_path(a.rejects_dir)
    lock_path = T.resolve_path(a.lock_file) if a.lock_file else LOCK_FILE
    results, malformed = [], []
    for p in a.results:
        try:
            results.append((p, C.load_json(T.resolve_path(p))))
        except OSError as ex:
            malformed.append((p, 'cannot read: %s' % (ex.strerror or ex)))
        except ValueError as ex:                      # JSONDecodeError / UnicodeDecodeError
            malformed.append((p, 'not valid JSON (utf-8): %s' % ex))
    for p, why in malformed:
        print('transmerge: malformed result file %s: %s' % (C._safe(p), C._safe(why)), file=sys.stderr)
    stale = []
    try:
        with (contextlib.nullcontext() if a.dry_run else MergeLock(lock_path, a.lock_timeout)):
            if not a.dry_run:
                stale = clean_stale_tmp(tdb, '.jsonl.tmp') + clean_stale_tmp(rejects_dir, '.json.tmp')
            db = T.load_db(tdb)                       # (re-)read INSIDE the lock: a concurrent merge may just have written
            rep, before = merge(db, results, shards, shard_file, a.overwrite, a.require_complete,
                                a.all_or_nothing, a.extra_lines, a.dry_run, backup_dir, rejects_dir, malformed)
    except LockTimeout as ex:
        print('transmerge: %s' % ex, file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, OSError) as ex:
        print('transmerge: %s' % ex, file=sys.stderr)
        return 2
    rep.stale_tmp = stale
    cov = coverage(db, shards_dir=shards)
    print(('DRY RUN (nothing written)\n' if a.dry_run else '') + format_merge(rep, before, count_en(db), cov))
    if rep.malformed:
        return 2
    return 1 if (rep.refused or rep.bad_entries) else 0


def cmd_status(a):
    db = T.load_db(T.resolve_path(a.tdb))
    cov = coverage(db, shards_dir=T.resolve_path(a.shards))
    if a.pending:
        for p in cov.get('shards', {}).get('pending_list', []):
            print(p['shard'] if not a.json else json.dumps(p))
        return 0
    if a.json:
        print(json.dumps(cov, ensure_ascii=False, indent=1))
    else:
        print(format_status(cov, a.all))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('merge')
    p.add_argument('results', nargs='+')
    p.add_argument('--tdb', default='translation')
    p.add_argument('--shards', default=T.SHARD_DIR)
    p.add_argument('--shard-file')
    p.add_argument('--backup-dir', default=T.BACKUP_DIR)
    p.add_argument('--rejects-dir', default=os.path.join(T.TRANS_DIR, 'rejects'))
    p.add_argument('--lock-file', help='merge lock file (default build/trans/merge.lock)')
    p.add_argument('--lock-timeout', type=float, default=LOCK_TIMEOUT, metavar='SECONDS',
                   help='how long to wait for another merge (default %g s)' % LOCK_TIMEOUT)
    p.add_argument('--overwrite', action='store_true', help='replace an existing different non-empty en')
    p.add_argument('--require-complete', action='store_true', help='items without a result count as failures')
    p.add_argument('--all-or-nothing', action='store_true', help='one failing item or malformed file refuses the whole run')
    p.add_argument('--extra-lines', type=int, default=0)
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_merge)
    p = sub.add_parser('status')
    p.add_argument('--tdb', default='translation')
    p.add_argument('--shards', default=T.SHARD_DIR)
    p.add_argument('--json', action='store_true')
    p.add_argument('--all', action='store_true', help='list source files without English too')
    p.add_argument('--pending', action='store_true', help='only print the shard numbers that still have work')
    p.set_defaults(fn=cmd_status)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
