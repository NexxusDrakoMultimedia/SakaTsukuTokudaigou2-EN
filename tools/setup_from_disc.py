# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""setup_from_disc: turn a fresh checkout of the public repository plus YOUR OWN disc into a tree the build tools can use.

The public repository holds only English text, identifiers, hashes and texture deltas (docs/l10n-format.md); the Japanese
text and the original textures come out of the disc you own.  One command does all of it:

    python -I -X utf8 tools/setup_from_disc.py "My Game.cue"          # or disc.gdi, or the volume .iso

  1. verify   the image against the hashes in tools/release.toml (tools/verify_source_disc.py); STOPS on any difference (exit 3)
  2. extract  every file of the disc except BCAST/BCAST.BIN into extracted/ (like tools/extract.py; files that already match the
              manifest l10n/disc-files.tsv are not rewritten), then checks the folder against the manifest
  3. l10n     l10n/*.jsonl + the disc -> translation/*.jsonl (+ refit/): the Japanese text is read from the disc by id and every
              string is checked against its recorded hash (tools/l10n.py import; any mismatch is listed by id and stops the run)
  4. textures l10n/textures/**/*.vcdiff + the extracted originals -> translation/textures/**/*.pvr (tools/texdelta.py apply-all)
  5. ready    prints the build command (tools/build_patch.py ...); nothing here builds the patch.

Everything written (extracted/, translation/) is gitignored local working data: never commit it.  Options:
    --extracted DIR   where the files go            (default extracted/)
    --translation DIR where the working form goes   (default translation/; an existing different file is only replaced with --force)
    --l10n DIR        the committed data            (default l10n/)
    --skip-extract    use an existing --extracted folder (it is still verified against the manifest)
    --skip-textures   do not run the texture step
    --keep-going      list every hash mismatch of the l10n step instead of stopping at the first bad file
    --force           replace differing files in --translation
    --dry-run         verify the disc, print the plan, write nothing
Exit status: 0 ready, 1 a step failed, 2 bad usage, 3 the disc is not the recorded dump.
"""
import argparse
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import l10n as L          # noqa: E402
import verify_source_disc as V   # noqa: E402

SKIP_EXTRACT = (V.BCAST_PATH,)


def extract_disc(disc, out_dir, manifest_rows=None, log=print):
    """Write every file of the disc (except BCAST.BIN) plus IP.BIN and _filelist.tsv below out_dir, like tools/extract.py.
    A file that already has the manifest's size and SHA-256 is left alone.  Returns (written, kept)."""
    known = {p: (size, sha) for p, lba, size, sha in (manifest_rows or [])}
    files = disc.files()
    os.makedirs(out_dir, exist_ok=True)
    written = kept = 0

    def current(path, p):
        want = known.get(p)
        return bool(want and os.path.isfile(path) and os.path.getsize(path) == want[0] and V.sha256_file(path) == want[1])

    ip = os.path.join(out_dir, 'IP.BIN')
    if current(ip, V.IP_PATH):
        kept += 1
    else:
        L.atomic_write(ip, disc.read(V.HD_BASE, 16 * V.USER))
        written += 1
    for p, lba, size in files:
        if p in SKIP_EXTRACT:
            continue
        dst = os.path.join(out_dir, *p.lstrip('/').split('/'))
        if current(dst, p):
            kept += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + '.tmp'
        with open(tmp, 'wb') as f:
            for chunk in disc.iter_file(lba, size):
                f.write(chunk)
        os.replace(tmp, dst)
        written += 1
    lines = ''.join('%s\t%d\t%d\n' % (p, lba, size) for p, lba, size in files)
    L.atomic_write(os.path.join(out_dir, '_filelist.tsv'), lines.encode('utf-8'))
    log('extracted: %d files written, %d already identical' % (written, kept))
    return written, kept


def apply_textures(l10n_dir, extracted, translation, log=print):
    """Step 4: the texture deltas.  Contract with tools/texdelta.py: apply_all(delta_dir, extracted_dir, out_dir)."""
    delta_dir = os.path.join(l10n_dir, 'textures')
    out_dir = os.path.join(translation, 'textures')
    if not os.path.isdir(delta_dir):
        log('textures: %s does not exist yet, nothing to apply' % delta_dir)
        return 0
    try:
        import texdelta
    except ImportError as e:
        log('textures: tools/texdelta.py is missing (%s); skipped' % e)
        return 1
    fn = getattr(texdelta, 'apply_all', None)
    if fn is None:
        log('textures: tools/texdelta.py has no apply_all(delta_dir, extracted_dir, out_dir); skipped')
        return 1
    try:
        res = fn(delta_dir, extracted, out_dir)
    except Exception as e:                                   # texdelta.TexDeltaError and friends: print, do not traceback
        log('textures: FAILED: %s' % e)
        return 1
    log('textures: applied into %s%s' % (out_dir, (' (%s)' % res) if isinstance(res, (int, str)) else ''))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('disc', help='.cue / .gdi / volume .iso of YOUR dump')
    ap.add_argument('--extracted', default=os.path.join(ROOT, 'extracted'))
    ap.add_argument('--translation', default=os.path.join(ROOT, 'translation'))
    ap.add_argument('--l10n', default=os.path.join(ROOT, 'l10n'))
    ap.add_argument('--skip-extract', action='store_true')
    ap.add_argument('--skip-textures', action='store_true')
    ap.add_argument('--keep-going', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', help='write the full list of l10n mismatches to this file')
    a = ap.parse_args(argv)
    t0 = time.time()
    log = lambda *x: print(*x, flush=True)
    a.extracted, a.translation, a.l10n = (os.path.abspath(p) for p in (a.extracted, a.translation, a.l10n))
    try:
        log('== 1/4 verify the disc')
        res = V.verify_disc(a.disc, log=log)
        log(res.text())
        if not res.ok:
            return 3
        L.check_manifest(a.l10n)
        if a.dry_run:
            log('dry run: would extract into %s, import %s into %s%s' % (
                a.extracted, a.l10n, a.translation, '' if a.skip_textures else ', apply the texture deltas'))
            return 0
        disc = V.SourceDisc(a.disc)
        try:
            log('== 2/4 extract the files')
            rows = V.read_manifest(os.path.join(a.l10n, L.DISC_FILES_NAME))
            if a.skip_extract:
                log('skipped (--skip-extract); checking the folder against the manifest')
            else:
                extract_disc(disc, a.extracted, rows, log)
            r = V.verify_extracted(a.extracted, os.path.join(a.l10n, L.DISC_FILES_NAME), log=log)
            log(r.text())
            if not r.ok:
                return 1
            log('== 3/4 import the translation (Japanese read from your disc, every string checked)')
            ns = argparse.Namespace(l10n=a.l10n, out=a.translation, disc=a.disc, extracted=a.extracted, keep_going=a.keep_going,
                                    report=a.report, max_report=200, force=a.force, no_verify=True, only=None)
            rc = L.cmd_import(ns, log)
            if rc:
                log('the l10n import failed: see the list above')
                return 1
        finally:
            disc.close()
        if a.skip_textures:
            log('== 4/4 textures skipped (--skip-textures)')
        else:
            log('== 4/4 texture deltas')
            if apply_textures(a.l10n, a.extracted, a.translation, log):
                log('the texture step reported a problem (see above); the text is imported, the repainted art is not')
                return 1
    except (V.VerifyError, L.L10nError) as e:
        print('error: %s' % e, file=sys.stderr)
        return 1
    log('')
    log('READY (%.0f s).  extracted/ and translation/ are local working data (gitignored).  Build the patch with e.g.' % (time.time() - t0))
    log('  python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on')
    log('(docs/pipeline.md section 9 lists the flags; tools/release.py makes the xdelta release from the result.)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
