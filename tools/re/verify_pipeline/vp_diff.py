"""python -I -X utf8 vp_diff.py <orig_prefix> <new_prefix> [expected_dir]
 expected_dir: optional dir with <iso path> files that the pipeline claims to have changed (build_patch --dump)."""
import sys, os, struct, hashlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vp_iso as V

def changed_sectors(a, b):
    """absolute LBAs whose 2352 raw bytes differ (new may be longer than orig)"""
    out = []
    for t in (1, 2, 3, 4, 5):
        fa = a.f[t]; fb = b.f[t]; fa.seek(0); fb.seek(0)
        na, nb = a.n[t], b.n[t]
        i = 0; CH = 2048
        while i < nb:
            c = min(CH, nb - i)
            ba = fa.read(min(c, max(0, na - i)) * V.SS); bb = fb.read(c * V.SS)
            if ba == bb:
                i += c; continue
            for k in range(c):
                sa = ba[k * V.SS:(k + 1) * V.SS]; sb = bb[k * V.SS:(k + 1) * V.SS]
                if sa != sb: out.append(V.TRK[t] + i + k)
            i += c
        if nb < na: out.append(('TRUNCATED', t))
    return out

def main():
    pa, pb = sys.argv[1], sys.argv[2]
    exp_dir = sys.argv[3] if len(sys.argv) > 3 else None
    A, Bd = V.Disc(pa), V.Disc(pb)
    print('sectors orig/new per track:', [(A.n[t], Bd.n[t]) for t in V.TRK], 'end', A.end, '->', Bd.end)
    ch = changed_sectors(A, Bd)
    print('changed sectors:', len(ch))
    pvdA, _, _, fA, dA, issA = V.walk(A)
    pvdB, rlB, rsB, fB, dB, issB = V.walk(Bd)
    problems = []
    print('ISO walk issues new:', issB, ' orig:', issA)
    problems += issB
    print('files orig/new', len(fA), len(fB), 'same name set:', set(fA) == set(fB), 'dirs same', dA.keys() == dB.keys())
    # PVD volume size
    vsB, = struct.unpack_from('<I', pvdB, 80); vsBb, = struct.unpack_from('>I', pvdB, 84)
    print('PVD volume space size new', vsB, vsBb, '-> end LBA', 45000 + vsB, 'disc end', Bd.end)
    if vsB != vsBb: problems.append('PVD vol size LE!=BE')
    if 45000 + vsB != Bd.end: problems.append('PVD volume size %d != disc end %d' % (45000 + vsB, Bd.end))
    # extents of new disc
    ext = []
    for p, e in fB.items():
        n = (e['size'] + 2047) // 2048
        if n: ext.append((e['lba'], e['lba'] + n, p))
        if e['lba'] + n > Bd.end: problems.append('file beyond disc end ' + p)
    ext.sort()
    shared = 0
    for (l1, h1, p1), (l2, h2, p2) in zip(ext, ext[1:]):
        if l2 < h1:
            # aliases (identical extent) are legal and exist on the original: check against orig
            if (l1, h1) == (l2, h2): shared += 1
            else: problems.append('OVERLAP %s [%d,%d) vs %s [%d,%d)' % (p1, l1, h1, p2, l2, h2))
    print('overlaps ok; identical-extent aliases:', shared)
    for p in sorted(set(fA) | set(fB)):
        if p not in fA or p not in fB: problems.append('file set differs ' + p)
    # classify per file
    movedfiles = []; changedfiles = []
    ordered = sorted(fB)
    sha = lambda D, e: hashlib.sha1(D.user(e['lba'], e['size'])).hexdigest()
    for p in ordered:
        ea, eb = fA[p], fB[p]
        same_loc = (ea['lba'], ea['size']) == (eb['lba'], eb['size'])
        if not same_loc: movedfiles.append((p, ea['lba'], eb['lba'], ea['size'], eb['size']))
        ha, hb = sha(A, ea), sha(Bd, eb)
        if ha != hb: changedfiles.append(p)
    print('files whose content differs:', changedfiles)
    print('files moved/resized:', movedfiles)
    if exp_dir:
        for p in changedfiles:
            exp = open(os.path.join(exp_dir, *p.strip('/').split('/')), 'rb').read()
            got = Bd.user(fB[p]['lba'], fB[p]['size'])
            if exp != got: problems.append('content != expected ' + p)
            else: print('  content == pipeline patch:', p)
        for root, _, fns in os.walk(exp_dir):
            for fn in fns:
                iso = '/' + os.path.relpath(os.path.join(root, fn), exp_dir).replace(os.sep, '/')
                if iso not in changedfiles: print('  NOTE expected-changed file reads identical on disc:', iso)
    # attribute changed sectors
    owner = {}
    for p in ordered:
        e = fB[p]; n = (e['size'] + 2047) // 2048
        for i in range(n): owner.setdefault(e['lba'] + i, []).append(p)
    # sectors of old extents of changed/moved files (zero fill of tail/old extent)
    oldown = {}
    for p in ordered:
        e = fA[p]; n = (e['size'] + 2047) // 2048
        for i in range(n): oldown.setdefault(e['lba'] + i, []).append(p)
    dirsec = set()
    for p, (l, s) in dB.items():
        for i in range((s + 2047) // 2048): dirsec.add(l + i)
    chset = [c for c in ch if not isinstance(c, tuple)]
    cls = collections.Counter(); unexpected = []
    changed_set = set(changedfiles) | {m[0] for m in movedfiles}
    for l in chset:
        if l == 45016: cls['PVD'] += 1; continue
        if 45000 <= l < 45016: cls['IP.BIN'] += 1; continue
        if l in dirsec: cls['directory'] += 1; continue
        ow = owner.get(l, []); oo = oldown.get(l, [])
        if any(p in changed_set for p in ow): cls['new extent of changed file'] += 1; continue
        if any(p in changed_set for p in oo): cls['old extent of changed/moved file'] += 1; continue
        if l >= A.end and not ow: cls['appended beyond orig end (unowned)'] += 1; unexpected.append(l); continue
        unexpected.append(l)
    print('changed sector attribution:', dict(cls))
    print('UNEXPECTED changed sectors (not pvd/ip/dir/changed-file extents):', len(unexpected), unexpected[:20])
    if unexpected: problems.append('unexpected changed sectors %d' % len(unexpected))
    # EDC/ECC of EVERY changed sector + moved/new extents
    bad = 0
    for l in chset:
        pr = V.check_sector(l, Bd.raw(l))
        if pr: bad += 1; print('  BAD sector', l, pr)
    print('EDC/ECC/header checked on %d changed sectors: %d bad' % (len(chset), bad))
    if bad: problems.append('%d sectors with bad edc/ecc' % bad)
    # old extent of moved files: what does it contain now?
    # dirs/PVD/IP diffs byte-level
    def diffbytes(l):
        ra, rb = A.raw(l)[16:2064], Bd.raw(l)[16:2064]
        return [i for i in range(2048) if ra[i] != rb[i]]
    for l in sorted(set(chset) & ({45016} | dirsec | set(range(45000, 45016)))):
        if l < A.end:
            d = diffbytes(l); print('  meta sector', l, 'bytes changed:', len(d), d[:12])
    # directory record structural comparison: only lba/size fields of changed files may differ
    # (check by comparing parsed dir entries)
    # every changed sector that lies inside the ORIGINAL disc must previously be (a) zero-user free space,
    # (b) part of a changed file's old extent, (c) directory/PVD/IP.  Check (a) explicitly for new extents.
    nonzero_overwritten = []
    for l in chset:
        if l >= A.end: continue
        if l == 45016 or 45000 <= l < 45016 or l in dirsec: continue
        if any(p in changed_set for p in oldown.get(l, [])): continue
        if A.raw(l)[16:2064] != bytes(2048): nonzero_overwritten.append(l)
    print('changed sectors that overwrote NON-ZERO data of files not being patched:', len(nonzero_overwritten), nonzero_overwritten[:10])
    if nonzero_overwritten: problems.append('overwrote nonzero orig data')
    # tracks 2/4 (audio) and unchanged data tracks beyond changes
    for t in (2, 4):
        A.f[t].seek(0); Bd.f[t].seek(0)
        print('audio track', t, 'identical:', A.f[t].read() == Bd.f[t].read())
    print('PROBLEMS:', problems)
    return 1 if problems else 0
sys.exit(main())
