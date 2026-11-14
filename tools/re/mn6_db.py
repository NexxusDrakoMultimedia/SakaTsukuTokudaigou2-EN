"""mn6_db.py: edit `en` of translation records by id, safely next to another workflow that edits the same files.

    import mn6_db;  mn6_db.apply({'FLOW_PRG/GETREP.BIN#27d00': ('old en or None', 'new en')}, dry=False)

Per file: ONE read-modify-write (read, change only the given ids, os.replace of a temp file in the same directory) so the window in which a
concurrent writer could be overwritten is a few milliseconds; unchanged lines are copied byte for byte.  A record whose current `en` is not the
expected old text is NOT changed (reported).  Returns (changed, skipped, missing)."""
import json
import os
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRANS = os.path.join(ROOT, 'translation')


def path_for(rid):
    return os.path.join(TRANS, rid.split('#')[0].replace('/', '__') + '.jsonl')


def dump(r):
    return json.dumps(r, ensure_ascii=False, separators=(',', ':'))


def apply(changes, dry=False):
    by = {}
    for rid, v in changes.items():
        by.setdefault(path_for(rid), {})[rid] = v
    changed, skipped, missing = [], [], []
    for p, ch in by.items():
        with open(p, 'rb') as f:
            raw = f.read()
        nl = b'\r\n' if b'\r\n' in raw else b'\n'
        lines = raw.decode('utf-8').split('\n')
        seen = set()
        out = []
        for ln in lines:
            s = ln.rstrip('\r')
            if s.strip():
                try:
                    r = json.loads(s)
                except ValueError:
                    r = None
                if r is not None and r.get('id') in ch:
                    old, new, *extra = ch[r['id']]
                    extra = extra[0] if extra else {}
                    seen.add(r['id'])
                    if old is not None and r.get('en') != old:
                        if r.get('en') == new:
                            pass
                        else:
                            skipped.append((r['id'], r.get('en'), old))
                    elif r.get('en') != new or any(r.get(k) != v for k, v in extra.items()):
                        sep = (',', ':') if dump(r) == s else (', ', ': ')          # keep the line's own JSON style
                        r['en'] = new
                        r.update(extra)
                        s = json.dumps(r, ensure_ascii=False, separators=sep)
                        changed.append(r['id'])
                    ln = s + ('\r' if ln.endswith('\r') else '')
            out.append(ln)
        missing += [i for i in ch if i not in seen]
        if not dry and any(i in changed for i in ch):
            data = '\n'.join(out).encode('utf-8')
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix='.mn6tmp')
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
            os.replace(tmp, p)
    return changed, skipped, missing


def records(pred):
    """[(id, record dict)] of every record for which pred(record) is true (read only)."""
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(TRANS, '*.jsonl'))):
        with open(p, encoding='utf-8') as f:
            for ln in f:
                if ln.strip():
                    r = json.loads(ln)
                    if pred(r):
                        out.append((r['id'], r))
    return out
