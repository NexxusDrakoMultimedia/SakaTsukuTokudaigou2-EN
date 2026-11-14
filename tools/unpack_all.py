"""Decode every container member under extracted/ into build/unpacked/.

Usage (from repo root):
    python -I -X utf8 tools/unpack_all.py [--src extracted] [--dst build/unpacked]
                                          [--no-write] [--scan-embedded]

Output layout: <dst>/<relative file path>/<member name>  (e.g.
build/unpacked/GAME/BINDFLAG.BIN/tex.pvr).  Duplicate member names inside one
file get a '~<member index>' suffix before the extension.  A global manifest
<dst>/_manifest.tsv records file, index, offset, method, sizes, name, status.

A file is treated as a container when a valid member record (including a
matching header CRC) starts at offset 0.  Everything except BCAST.BIN (and the
tool-generated _filelist.tsv) is examined.  extracted/ is only read.
"""
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bzlib  # noqa: E402

SKIP_NAMES = {'BCAST.BIN', '_filelist.tsv'}


def safe_name(name, idx, used):
    s = name or ('member%04d' % idx)
    s = ''.join('_' if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in s).strip(' .') or ('member%04d' % idx)
    if s.lower() in used:
        base, ext = os.path.splitext(s)
        s = '%s~%d%s' % (base, idx, ext)
    used.add(s.lower())
    return s


def looks_like_header(data):
    return len(data) > 8 and data[2] == 0x2D and data[6] == 0x2D


def scan_embedded(data, start=0):
    """Offsets >= start where a valid, header-CRC-checked member record lies."""
    hits = []
    for pat in (b'-nc--', b'-bz--', b'-bzw-'):
        k = data.find(pat, start + 2)
        while k != -1:
            o = k - 2
            m = bzlib.parse_member(data, o, with_data=False)
            if m is not None and m.hdr_crc_ok:
                hits.append(o)
            k = data.find(pat, k + 1)
    return sorted(hits)


def embedded_runs(data, start=0):
    """Group CRC-valid embedded records into runs of back-to-back members.
    Returns list of (run_start_offset, [Member...])."""
    runs = []
    covered = start
    for o in scan_embedded(data, start):
        if o < covered:
            continue
        ms = []
        p = o
        while True:
            m = bzlib.parse_member(data, p)
            if m is None or not m.hdr_crc_ok:
                break
            ms.append(m)
            p = (m.end_offset + 3) & ~3
        if ms:
            runs.append((o, ms))
            covered = p
    return runs


def write_embedded(rel, data, start, dst, write, st, manifest, problems):
    for o, ms in embedded_runs(data, start):
        used = set()
        outdir = os.path.join(dst, rel, '@%x' % o)
        if write:
            os.makedirs(outdir, exist_ok=True)
        for idx, m in enumerate(ms):
            st['embedded_members'] += 1
            status = 'OK'
            plain = None
            try:
                plain = bzlib.decompress(m.packed, m.orig_size, m.method)
                if bzlib.crc16(plain) != m.crc16:
                    status = 'CRC_MISMATCH'
            except Exception as e:
                status = 'DECODE_ERROR: %s' % e
            if status == 'OK':
                st['embedded_ok'] += 1
            else:
                st['embedded_bad'] += 1
                problems.append((rel, m.offset, 'embedded %s %s' % (m.name, status)))
            nm = safe_name(m.name, idx, used)
            manifest.append('\t'.join(map(str, [rel.replace('\\', '/') + '/@%x' % o, idx, m.offset, m.method,
                                                m.packed_size, m.orig_size, nm, status])))
            if write and plain is not None:
                with open(os.path.join(outdir, nm), 'wb') as f:
                    f.write(plain)


def main(argv):
    src, dst = 'extracted', os.path.join('build', 'unpacked')
    write = True
    scan = False
    it = iter(argv)
    for a in it:
        if a == '--src':
            src = next(it)
        elif a == '--dst':
            dst = next(it)
        elif a == '--no-write':
            write = False
        elif a == '--scan-embedded':
            scan = True
        else:
            print('unknown arg', a)
            return 2
    st = collections.Counter()
    problems = []
    notes = []
    manifest = []
    containers = 0
    noncont = []
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for fn in sorted(files):
            if fn.upper() == 'BCAST.BIN' or fn in SKIP_NAMES:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, src)
            with open(path, 'rb') as f:
                data = f.read()
            st['files'] += 1
            first = bzlib.parse_member(data, 0, with_data=False)
            if first is None:
                if looks_like_header(data) and data[2:7] not in (b'-nc--', b'-bz--', b'-bzw-'):
                    st['unknown_method_files'] += 1
                    problems.append((rel, 0, 'unknown method %r' % bytes(data[2:7])))
                else:
                    st['non_container_files'] += 1
                    noncont.append((rel, len(data)))
                    if scan:
                        n0 = st['embedded_members']
                        write_embedded(rel, data, 0, dst, write, st, manifest, problems)
                        if st['embedded_members'] > n0:
                            st['noncontainer_files_with_embedded'] += 1
                continue
            containers += 1
            members, tail = bzlib.parse_archive(data)
            if tail != len(data):
                st['files_with_unparsed_tail'] += 1
                bad = data[tail:tail + 8]
                kind = 'unknown method' if looks_like_header(data[tail:]) and \
                    bytes(data[tail + 2:tail + 7]) not in (b'-nc--', b'-bz--', b'-bzw-') else 'unparsed tail'
                if kind == 'unknown method':
                    st['unknown_method'] += 1
                    problems.append((rel, tail, 'unknown method at tail'))
                notes.append((rel, tail, '%s (%d bytes left, starts %s)' % (kind, len(data) - tail, bad.hex())))
                if scan:
                    n0 = st['embedded_members']
                    write_embedded(rel, data, tail, dst, write, st, manifest, problems)
                    if st['embedded_members'] > n0:
                        st['container_tails_with_embedded'] += 1
            used = set()
            outdir = os.path.join(dst, rel)
            if write:
                os.makedirs(outdir, exist_ok=True)
            for idx, m in enumerate(members):
                st['members'] += 1
                st['method ' + m.method] += 1
                status = 'OK'
                plain = None
                try:
                    plain = bzlib.decompress(m.packed, None, m.method)
                except Exception as e:
                    status = 'DECODE_ERROR: %s' % e
                    st['decode_error'] += 1
                if plain is not None:
                    if len(plain) != m.orig_size:
                        status = 'LEN_MISMATCH %d != %d' % (len(plain), m.orig_size)
                        st['len_mismatch'] += 1
                    elif bzlib.crc16(plain) != m.crc16:
                        status = 'CRC_MISMATCH'
                        st['crc_mismatch'] += 1
                    else:
                        st['members_ok'] += 1
                if m.hdr_crc_ok is False:
                    st['header_crc_bad'] += 1
                    status += ' HDRCRC_BAD'
                if status != 'OK':
                    problems.append((rel, m.offset, '%s %s' % (m.name, status)))
                nm = safe_name(m.name, idx, used)
                manifest.append('\t'.join(map(str, [rel.replace('\\', '/'), idx, m.offset, m.method, m.packed_size,
                                                    m.orig_size, nm, status])))
                if write and plain is not None:
                    with open(os.path.join(outdir, nm), 'wb') as f:
                        f.write(plain)
                    st['bytes_written'] += len(plain)
    if write:
        os.makedirs(dst, exist_ok=True)
        with open(os.path.join(dst, '_manifest.tsv'), 'w', encoding='utf-8') as f:
            f.write('file\tindex\toffset\tmethod\tpacked\torig\tname\tstatus\n')
            f.write('\n'.join(manifest) + '\n')
    print('files examined          :', st['files'])
    print('container files         :', containers)
    print('non-container files     :', st['non_container_files'])
    print('members total           :', st['members'])
    for m in bzlib.METHODS:
        print('  method %-6s        : %d' % (m, st['method ' + m]))
    print('members OK (len+crc)    :', st['members_ok'])
    print('mismatched length       :', st['len_mismatch'])
    print('crc mismatch            :', st['crc_mismatch'])
    print('decode errors           :', st['decode_error'])
    print('header crc bad          :', st['header_crc_bad'])
    print('unknown method (members):', st['unknown_method'], ' (files whose 1st member is unknown:', st['unknown_method_files'], ')')
    print('files with unparsed tail:', st['files_with_unparsed_tail'])
    if scan:
        print('embedded members (CRC-valid header in non-container files / container tails):', st['embedded_members'])
        print('  OK:', st['embedded_ok'], ' bad:', st['embedded_bad'],
              ' non-container files involved:', st['noncontainer_files_with_embedded'],
              ' container tails involved:', st['container_tails_with_embedded'])
    for p in notes[:5]:
        print('NOTE', p)
    if len(notes) > 5:
        print('... %d more notes (files whose member list ends before EOF; tail is not a member record)' % (len(notes) - 5))
    print('bytes written           :', st['bytes_written'] if write else '(no-write)')
    for p in problems[:40]:
        print('PROBLEM', p)
    if len(problems) > 40:
        print('... %d more problems' % (len(problems) - 40))
    return 0 if not problems else 1  # notes (unparsed tails) are informational


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
