"""skt_patch: apply the skeptic fixes to tools/texdelta.py (exact-string replacements, each must match once)."""
import os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'texdelta.py')
s = open(P, encoding='utf-8', newline='').read()
NL = '\r\n' if '\r\n' in s else '\n'
s = s.replace('\r\n', '\n')


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


rep("import argparse\nimport hashlib\nimport os\n", "import argparse\nimport hashlib\nimport lzma\nimport os\n")
rep('''def sha256(b):
    return hashlib.sha256(b).hexdigest()
''', '''MAX_TARGET = 64 * 1024 * 1024     # a texture file is a few MB at most; a delta that claims more is damaged or hostile


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def write_atomic(path, data):
    """Write data to path through a temporary file in the same directory, then os.replace: a crash or Ctrl-C leaves
    the old file or no file, never a half-written one."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = '%s.tmp%d' % (path, os.getpid())
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def safe_rel(rel):
    """A manifest path must be a relative '/'-separated path below the output directory ending in .pvr."""
    parts = rel.split('/')
    if (not rel.lower().endswith('.pvr') or '\\\\' in rel or ':' in rel or rel.startswith('/') or
            any(p in ('', '.', '..') for p in parts)):
        raise TexDeltaError('unsafe or malformed path in the manifest: %r' % rel)
    return rel
''')
rep('''    _, windows = V.parse(delta)
    out = bytearray()
    for w in windows:
        if w.indicator & V.VCD_TARGET:
            raise TexDeltaError('VCD_TARGET windows are not used by texture deltas')
        seg = b''
        if w.indicator & V.VCD_SOURCE:
            seg = bytes(src[w.seg_pos:w.seg_pos + w.seg_len])
            if len(seg) != w.seg_len:
                raise TexDeltaError('original texture is shorter than the delta expects (wrong disc revision?)')
        out += V.decode_window(w, seg)
    return bytes(out)
''', '''    try:
        _, windows = V.parse(delta)
        out = bytearray()
        for w in windows:
            if w.indicator & V.VCD_TARGET:
                raise TexDeltaError('VCD_TARGET windows are not used by texture deltas')
            if w.tgt_len > MAX_TARGET or len(out) + w.tgt_len > MAX_TARGET:
                raise TexDeltaError('delta claims a result of %d bytes: damaged delta' % w.tgt_len)
            seg = b''
            if w.indicator & V.VCD_SOURCE:
                seg = bytes(src[w.seg_pos:w.seg_pos + w.seg_len])
                if len(seg) != w.seg_len:
                    raise TexDeltaError('original texture is shorter than the delta expects (wrong disc revision?)')
            out += V.decode_window(w, seg)
        return bytes(out)
    except TexDeltaError:
        raise
    except (ValueError, IndexError, EOFError, OverflowError, MemoryError, lzma.LZMAError) as e:
        # vcdiff.py and the xz decoder raise their own types on damaged input: always report them as ours
        raise TexDeltaError('damaged delta (%s: %s)' % (type(e).__name__, e))
''')
rep('''        dst = os.path.join(out_dir, *rel[:-4].split('/')) + DELTA_EXT
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(delta)
        rows.append''', '''        dst = os.path.join(out_dir, *rel[:-4].split('/')) + DELTA_EXT
        write_atomic(dst, delta)
        rows.append''')
rep('''    write_manifest(os.path.join(out_dir, MANIFEST), rows)
    if problems:''', '''    write_manifest(os.path.join(out_dir, MANIFEST), rows)
    if not problems:
        _prune(out_dir, rows)
    if problems:''')
rep('''def write_manifest(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\\n') as f:
        f.write('# texdelta manifest (docs/texture-delta.md). Columns, tab separated:\\n')
        f.write('# path (working file below translation/textures/) | sha256 of the repainted PVR | '
                'sha256 of the ORIGINAL texture (PVR bytes as tools/texinject.py extract_pvr gives them) | delta bytes\\n')
        for r in sorted(rows):
            f.write('%s\\t%s\\t%s\\t%d\\n' % r)
''', '''def _prune(out_dir, rows):
    """Remove .vcdiff files below out_dir that no manifest row names (a texture that was deleted or renamed since an
    earlier make); a stale delta would otherwise ship with the next release."""
    keep = {os.path.normpath(os.path.join(out_dir, *r[0][:-4].split('/')) + DELTA_EXT) for r in rows}
    for full in list(_walk(out_dir, DELTA_EXT)):
        if os.path.normpath(full) not in keep:
            os.remove(full)
    for dp, dns, fns in os.walk(out_dir, topdown=False):
        if dp != out_dir and not os.listdir(dp):
            os.rmdir(dp)


def write_manifest(path, rows):
    text = ('# texdelta manifest (docs/texture-delta.md). Columns, tab separated:\\n'
            '# path (working file below translation/textures/) | sha256 of the repainted PVR | '
            'sha256 of the ORIGINAL texture (PVR bytes as tools/texinject.py extract_pvr gives them) | delta bytes\\n')
    text += ''.join('%s\\t%s\\t%s\\t%d\\n' % r for r in sorted(rows))
    write_atomic(path, text.encode('utf-8'))
''')
rep('''            rows.append((p[0], p[1], p[2], int(p[3])))
    return rows''', '''            try:
                n_bytes = int(p[3])
            except ValueError:
                raise TexDeltaError('%s:%d: malformed manifest line' % (path, n))
            rows.append((safe_rel(p[0]), p[1], p[2], n_bytes))
    if len({r[0] for r in rows}) != len(rows):
        raise TexDeltaError('%s: a path is listed twice' % path)
    return rows''')
rep('''            problems.append('%s: %s' % (rel, e if isinstance(e, TexDeltaError) else '%s: %s' % (type(e).__name__, e)))
            continue
        dst = os.path.join(out_dir, *rel.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(out)
        done.append(rel)''', '''            msg = str(e) if isinstance(e, TexDeltaError) else '%s: %s' % (type(e).__name__, e)
            problems.append(msg if msg.startswith(rel + ':') else '%s: %s' % (rel, msg))
            continue
        write_atomic(os.path.join(out_dir, *rel.split('/')), out)
        done.append(rel)''')
rep('''    return done, problems


# =============================================================== verify''', '''    listed = {os.path.normpath(os.path.join(delta_dir, *r[0][:-4].split('/')) + DELTA_EXT) for r in rows}
    for full in _walk(delta_dir, DELTA_EXT):
        if os.path.normpath(full) not in listed:
            problems.append('%s: delta file is not listed in %s (stale or foreign file; it was not applied)'
                            % (_rel(full, delta_dir), MANIFEST))
    return done, problems


# =============================================================== verify''')
rep('''        out = apply_bytes(d, o, what=a.delta)
        with open(a.out, 'wb') as f:
            f.write(out)''', '''        out = apply_bytes(d, o, what=a.delta)
        write_atomic(a.out, out)''')
open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', NL))
print('patched')
