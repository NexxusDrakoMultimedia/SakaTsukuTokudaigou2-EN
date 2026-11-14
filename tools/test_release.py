"""Fast self-test of the xdelta release tooling (tools/release.py, apply_patch.py, discformat.py, isoexport.py).
Run:  python -I -X utf8 tools/test_release.py            (~10 s; the full build is a manual step, docs/RELEASING.md)

 1  repo facts: tools/release.toml sizes/layout agree with the real track files and tools/discbuild.py, the real
    .cue and discbuild's .gdi parse to the right track -> file maps, volume ISO size = PVD volume size.
 2  format detection (sniff/open_disc) on synthetic files: cue, gdi, volume ISO, full ISO, ordinary ISO,
    raw single track, 2048-byte track iso, unknown; refusal messages; gdi with 2048-byte sectors; single-bin cue.
 3  isoexport on a tiny synthetic disc: raw Mode 1 -> cooked, zero fill for audio/pregap, growth.
 4  release.produce + apply_patch.py (as a subprocess, like a player) on a tiny synthetic disc in the three forms
    (cue, gdi with renamed tracks, volume iso): result byte-equal to the built tracks, --verify states, output never
    over the source, refusal on a wrong/corrupt dump (nothing written), already-patched detection, empty release
    (nothing changed), xdelta3 cross-check when xdelta3 is installed.
 5  the shipped player files parse as Python 3.8.
 6  the real translators' notes (doc/TRANSLATORS_NOTES.md): no PLACEHOLDER, main sections, hashes equal release.toml,
    money examples add up, bundled unchanged into a tiny release.
Writes only below build/test_release/.
"""
import ast
import json
import os
import random
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import discformat as DF   # noqa: E402
import isoexport          # noqa: E402
import discbuild as D     # noqa: E402
import release as R       # noqa: E402

WORK = os.path.join(ROOT, 'build', 'test_release')
T0 = time.time()
RESULTS = []


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    log(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        raise AssertionError(msg)


def expect_error(fn, text, msg):
    try:
        fn()
    except DF.DiscError as e:
        check(text in str(e), msg + ' -> "%s"' % str(e)[:90])
        return
    check(False, msg + ' (no error raised)')


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)


def get(path):
    with open(path, 'rb') as f:
        return f.read()


# ------------------------------------------------------------------ 1
def test_repo_facts():
    log('--- 1: repo facts')
    cfg = R.load_config()
    lay = R.game_layout()
    end = 0
    for n in range(1, 6):
        h = R.recorded(cfg, 'track%d' % n)
        p = os.path.join(ROOT, D.BASE % n)
        check(os.path.getsize(p) == h['size'], 'release.toml size of track %d = file size (%d)' % (n, h['size']))
        check(h['size'] % 2352 == 0, '  whole sectors')
    iso = R.recorded(cfg, 'volume_iso')
    end = lay['tracks'][5]['lba'] + cfg['source']['track5']['size'] // 2352
    check(iso['size'] == (end - lay['hd_base']) * 2048, 'volume ISO size %d = (end LBA %d - 45000) * 2048' % (iso['size'], end))
    # PVD volume space size of the real disc (read through gdrom) equals the ISO sector count
    import gdrom
    d = gdrom.Disc(ROOT)
    pvd = d.read(45016, 2048)
    vss = int.from_bytes(pvd[80:84], 'little')
    check(vss * 2048 == iso['size'], 'PVD volume space size %d sectors == volume ISO sectors' % vss)
    cue = DF.parse_cue(os.path.join(ROOT, D.BASE.replace(' (Track %d).bin', '.cue')))
    check([os.path.basename(e['file']) for e in cue] == [D.BASE % n for n in range(1, 6)]
          and [e['type'] for e in cue] == ['MODE1/2352', 'AUDIO', 'MODE1/2352', 'AUDIO', 'MODE1/2352'],
          'real .cue parses: 5 tracks, one file each, Redump names')
    os.makedirs(WORK, exist_ok=True)
    gp = os.path.join(WORK, 'x.gdi')
    put(gp, D.gdi_text('X').encode())
    g = DF.parse_gdi(gp)
    check([e['lba'] for e in g] == [D.TRACK_LBA[n] for n in range(1, 6)] and all(e['secsize'] == 2352 for e in g),
          'discbuild .gdi parses (lbas %s)' % [e['lba'] for e in g])
    check(R.GDI_NAMES[3] == 'track03.bin' and R.GDI_NAMES[4] == 'track04.raw', 'GDI names mapped')


# ------------------------------------------------------------------ tiny disc
TINY = {'title': 'Tiny Test Game', 'hd_base': 100,
        'tracks': {1: {'kind': 'data', 'lba': 0, 'redump_name': 'tiny (Track 1).bin', 'gdi_name': 'track01.bin'},
                   2: {'kind': 'audio', 'lba': 10, 'redump_name': 'tiny (Track 2).bin', 'gdi_name': 'track02.raw'},
                   3: {'kind': 'data', 'lba': 100, 'redump_name': 'tiny (Track 3).bin', 'gdi_name': 'track03.bin'},
                   4: {'kind': 'audio', 'lba': 120, 'redump_name': 'tiny (Track 4).bin', 'gdi_name': 'track04.raw'},
                   5: {'kind': 'data', 'lba': 125, 'redump_name': 'tiny (Track 5).bin', 'gdi_name': 'track05.bin'}}}


def make_tiny(rng, grow=0, edits=True):
    """(users, raws, tracks): user data per data track, raw bytes per track."""
    def users(n, first=None):
        out = [bytes(rng.getrandbits(8) for _ in range(2048)) for _ in range(n)]
        return out
    u3 = users(20)
    u3[0] = b'SEGA SEGAKATANA'.ljust(2048, b'\0')
    u3[16] = b'\x01CD001\x01'.ljust(2048, b'\0')
    u1 = users(3)
    u5 = users(25)
    audio2 = bytes(rng.getrandbits(8) for _ in range(2352 * 4))
    audio4 = bytes(rng.getrandbits(8) for _ in range(2352 * 5))
    return {'u1': u1, 'u3': u3, 'u5': u5, 'a2': audio2, 'a4': audio4}


def raw_track(lba, users, pregap_zero=0):
    out = bytearray()
    for i in range(pregap_zero):
        out += bytes(2352)
    for i, u in enumerate(users[pregap_zero:], start=pregap_zero):
        out += D.encode_sector(lba + i, u)
    return bytes(out)


def tiny_tracks(d):
    t = {1: raw_track(0, d['u1']), 2: d['a2'], 3: raw_track(100, d['u3']), 4: d['a4'],
         5: raw_track(125, d['u5'], pregap_zero=5)}
    return t


def write_tiny(dirname, tracks, naming, sheet):
    """naming 'redump' or 'gdi'; returns sheet path."""
    for n, data in tracks.items():
        name = TINY['tracks'][n]['redump_name' if naming == 'redump' else 'gdi_name']
        put(os.path.join(dirname, name), data)
    if sheet == 'cue':
        txt = ''.join('FILE "%s" BINARY\r\n  TRACK %02d %s\r\n    INDEX 01 00:00:00\r\n' % (
            TINY['tracks'][n]['redump_name'], n, 'MODE1/2352' if TINY['tracks'][n]['kind'] == 'data' else 'AUDIO')
            for n in range(1, 6))
        p = os.path.join(dirname, 'tiny.cue')
    else:
        txt = '5\r\n' + ''.join('%d %d %d 2352 %s 0\r\n' % (
            n, TINY['tracks'][n]['lba'], 4 if TINY['tracks'][n]['kind'] == 'data' else 0, TINY['tracks'][n]['gdi_name'])
            for n in range(1, 6))
        p = os.path.join(dirname, 'disc.gdi')
    put(p, txt.encode())
    return p


# ------------------------------------------------------------------ 2
def test_detect():
    log('--- 2: format detection')
    base = os.path.join(WORK, 'detect')
    shutil.rmtree(base, ignore_errors=True)
    rng = random.Random(1)
    d = make_tiny(rng)
    tr = tiny_tracks(d)
    cue = write_tiny(os.path.join(base, 'cue'), tr, 'redump', 'cue')
    gdi = write_tiny(os.path.join(base, 'gdi'), tr, 'gdi', 'gdi')
    disc = DF.open_disc(cue)
    check(disc.kind == 'cue' and sorted(disc.tracks) == [1, 2, 3, 4, 5], 'cue detected, 5 tracks mapped')
    disc = DF.open_disc(gdi)
    check(disc.kind == 'gdi' and os.path.basename(disc.tracks[5]) == 'track05.bin', 'gdi detected, track05.bin mapped')
    # sniffing without the extension
    cue2 = os.path.join(base, 'cue', 'sheet.txt')
    shutil.copy(cue, cue2)
    check(DF.sniff(cue2)[0] == 'cue', 'cue sheet recognised by content')
    # volume iso (HD_BASE lowered for the tiny disc is irrelevant here: PVD at sector 16)
    iso = os.path.join(base, 'v.iso')
    isoexport.export_volume_iso([(100, 'data', os.path.join(base, 'cue', 'tiny (Track 3).bin')),
                                 (120, 'audio', os.path.join(base, 'cue', 'tiny (Track 4).bin')),
                                 (125, 'data', os.path.join(base, 'cue', 'tiny (Track 5).bin'))], iso, 100)
    check(DF.sniff(iso)[0] == 'volume-iso' and DF.open_disc(iso).kind == 'iso', 'volume ISO detected (IP.BIN + PVD at sector 16)')
    # others
    plain = os.path.join(base, 'plain.iso')
    put(plain, (b'\0' * 2048 * 16) + b'\x01CD001\x01'.ljust(2048, b'\0') + b'\0' * 2048)
    check(DF.sniff(plain)[0] == 'iso-no-ip', 'ordinary ISO9660 without IP.BIN classified')
    expect_error(lambda: DF.open_disc(plain), 'without the Dreamcast IP.BIN', 'ordinary ISO refused')
    old = DF.HD_BASE
    DF.HD_BASE = 100
    try:
        full = os.path.join(base, 'full.iso')
        put(full, b'\0' * (2048 * 116) + b'\x01CD001\x01'.ljust(2048, b'\0') + b'\0' * 2048)
        check(DF.sniff(full)[0] == 'full-iso', 'ISO addressed from LBA 0 (PVD at 45016 on the real disc) classified')
        expect_error(lambda: DF.open_disc(full), 'starts at LBA 0', 'full ISO refused')
    finally:
        DF.HD_BASE = old
    expect_error(lambda: DF.open_disc(os.path.join(base, 'cue', 'tiny (Track 3).bin')), 'single raw track', 'lone raw track refused')
    t3 = os.path.join(base, 't3.iso')
    put(t3, get(iso)[:2048 * 20])
    junk = os.path.join(base, 'junk.dat')
    put(junk, b'hello' * 1000)
    expect_error(lambda: DF.open_disc(junk), 'not a .cue, .gdi', 'unknown file refused')
    # gdi with 2048-byte sectors
    g2 = os.path.join(base, 'g2', 'disc.gdi')
    put(g2, b'5\r\n' + b''.join(b'%d 0 4 2048 track0%d.iso 0\r\n' % (n, n) for n in range(1, 6)))
    expect_error(lambda: DF.open_disc(g2), '2048-byte', 'gdi with cooked tracks refused')
    # single-bin cue
    sb = os.path.join(base, 'sb', 'one.cue')
    put(sb, b'FILE "all.bin" BINARY\r\n TRACK 01 MODE1/2352\r\n INDEX 01 00:00:00\r\n TRACK 02 AUDIO\r\n INDEX 01 00:02:00\r\n')
    expect_error(lambda: DF.open_disc(sb), 'one file per track', 'single-bin cue refused')
    # missing track file
    miss = os.path.join(base, 'miss')
    shutil.copytree(os.path.join(base, 'cue'), miss)
    os.remove(os.path.join(miss, 'tiny (Track 4).bin'))
    expect_error(lambda: DF.open_disc(os.path.join(miss, 'tiny.cue')), 'does not exist', 'missing track file reported')


# ------------------------------------------------------------------ 3
def test_export():
    log('--- 3: isoexport')
    base = os.path.join(WORK, 'export')
    shutil.rmtree(base, ignore_errors=True)
    rng = random.Random(2)
    d = make_tiny(rng)
    tr = tiny_tracks(d)
    for n, data in tr.items():
        put(os.path.join(base, 't%d.bin' % n), data)
    iso = os.path.join(base, 'v.iso')
    nsec = isoexport.export_volume_iso([(100, 'data', os.path.join(base, 't3.bin')), (120, 'audio', os.path.join(base, 't4.bin')),
                                        (125, 'data', os.path.join(base, 't5.bin'))], iso, 100)
    data = get(iso)
    check(nsec == 50 and len(data) == 50 * 2048, 'ISO has (end 150 - 100) = 50 sectors')
    cooked_ok = all(data[i * 2048:(i + 1) * 2048] == d['u3'][i] for i in range(20))
    check(cooked_ok, 'track 3 sectors cooked to their 2048 user bytes')
    check(data[20 * 2048:25 * 2048] == bytes(5 * 2048), 'audio track area is zero sectors')
    check(data[25 * 2048:30 * 2048] == bytes(5 * 2048), 'all-zero raw pregap sectors cook to zero')
    check(all(data[(30 + i) * 2048:(31 + i) * 2048] == d['u5'][5 + i] for i in range(20)), 'track 5 data sectors cooked')
    bad = bytearray(tr[3])
    bad[2352 * 4 + 15] = 2
    put(os.path.join(base, 'bad.bin'), bytes(bad))
    expect_error(lambda: isoexport.export_volume_iso([(100, 'data', os.path.join(base, 'bad.bin'))], iso + '2', 100),
                 'mode 2', 'a non-Mode-1 sector is refused')
    junk = bytearray(tr[3])
    junk[2352 * 4 + 5] = 9          # damage the sync pattern
    put(os.path.join(base, 'junk.bin'), bytes(junk))
    expect_error(lambda: isoexport.export_volume_iso([(100, 'data', os.path.join(base, 'junk.bin'))], iso + '2', 100),
                 'no sync pattern', 'a damaged sector is refused')
    check(not os.path.exists(iso + '2') and not os.path.exists(iso + '2.partial'), 'no partial output left behind')


# ------------------------------------------------------------------ 4
def run_apply(patcher, *args):
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', patcher] + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, r.stdout + r.stderr


NOTES_TEXT = b'# Translators notes\n\nThe real notes of the tiny test game.\n'
CHANGELOG_TEXT = b'# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-02\n\n### Added\n\n- the tiny test game\n'


def build_release(base, label, src_users, new_users, grow=0, x3=None, tweak=None, notes_text=NOTES_TEXT, allow=False, raw=True,
                  changelog_text=CHANGELOG_TEXT):
    """tiny source tracks + built tracks -> release folder; returns (dist dir, manifest, src/built track dicts)."""
    src_tr = tiny_tracks(src_users)
    built_tr = tiny_tracks(new_users)
    if tweak:
        tweak(built_tr)
    notes = os.path.join(base, label + '_notes.md')
    put(notes, notes_text)
    w = os.path.join(base, label + '_work')
    os.makedirs(w, exist_ok=True)
    sf, bf, sh, bh = {}, {}, {}, {}
    for n in range(1, 6):
        sf[n] = os.path.join(w, 's%d.bin' % n)
        bf[n] = os.path.join(w, 'b%d.bin' % n)
        put(sf[n], src_tr[n])
        put(bf[n], built_tr[n])
        sh[n] = DF.hash_file(sf[n])
        bh[n] = DF.hash_file(bf[n])
    hd = lambda fs: [(100, 'data', fs[3]), (120, 'audio', fs[4]), (125, 'data', fs[5])]
    sf['iso'], bf['iso'] = os.path.join(w, 's.iso'), os.path.join(w, 'b.iso')
    isoexport.export_volume_iso(hd(sf), sf['iso'], 100)
    isoexport.export_volume_iso(hd(bf), bf['iso'], 100)
    sh['iso'], bh['iso'] = DF.hash_file(sf['iso']), DF.hash_file(bf['iso'])
    chl = os.path.join(base, label + '_changelog.md')
    put(chl, changelog_text)
    lic = os.path.join(base, label + '_licenses')
    put(os.path.join(lic, 'GPL-3.0-or-later.txt'), b'GPL test text\n')
    put(os.path.join(lic, 'CC-BY-SA-4.0.txt'), b'CC test text\n')
    out = os.path.join(base, label + '_dist', 'T-1.0.0')
    shutil.rmtree(out, ignore_errors=True)
    man = R.produce(TINY, '1.0.0', '2026-01-02', sf, sh, bf, bh, out, w, project='Tiny-EN', x3=x3,
                    git_commit=None, build_text='summary\n', notes=notes, allow_placeholder=allow, raw_patches=raw,
                    changelog=chl, licenses_dir=lic)
    R.write_sha256sums(out)
    return out, man, src_tr, built_tr


def test_apply():
    log('--- 4: release.produce + apply_patch.py on a tiny disc')
    base = os.path.join(WORK, 'apply')
    shutil.rmtree(base, ignore_errors=True)
    rng = random.Random(3)
    src_users = make_tiny(rng)
    new_users = {k: (list(v) if isinstance(v, list) else v) for k, v in src_users.items()}
    new_users['u3'][5] = bytes(rng.getrandbits(8) for _ in range(2048))
    new_users['u3'][18] = bytes(2048)
    new_users['u5'] = new_users['u5'][:10] + [bytes(rng.getrandbits(8) for _ in range(2048))] + new_users['u5'][11:] \
        + [bytes(rng.getrandbits(8) for _ in range(2048)) for _ in range(3)]       # track 5 grows by 3 sectors
    new_users['u5'][20], new_users['u5'][21] = src_users['u5'][7], src_users['u5'][8]      # a 2-sector file moves
    new_users['u5'][7], new_users['u5'][8] = bytes(2048), bytes(2048)
    x3 = R.find_xdelta3()
    out, man, src_tr, built_tr = build_release(base, 'a', src_users, new_users, x3=x3)
    check(man['tracks']['3']['changed'] and man['tracks']['5']['changed'], 'tracks 3 and 5 changed')
    check(not any(man['tracks'][n]['changed'] for n in '124'), 'tracks 1, 2, 4 unchanged, no patch file')
    check(man['volume_iso']['changed'], 'volume ISO changed')
    check(man['volume_iso']['patch']['moved_sectors'] == 2 and man['tracks']['5']['patch']['moved_sectors'] == 2,
          'the encoder found the moved 2-sector file in the ISO patch and in the raw track 5 patch')
    check(man['manifest_version'] == 2 and sorted(man['raw_rebuild']) == ['3', '5'] and all(man['raw_rebuild'].values()),
          'manifest v2: raw tracks 3 and 5 can be rebuilt from the patched ISO (%s)' % man['raw_rebuild'])
    names = sorted(os.listdir(out))
    check(all(x in names for x in ('MANIFEST.json', 'HASHES.txt', 'SHA256SUMS', 'README.md', 'apply_patch.py', 'verify_dist.py',
                                   'TRANSLATORS_NOTES.md', 'LICENSE', 'NOTICE.txt', 'Tiny-EN-1.0.0-track03.xdelta',
                                   'Tiny-EN-1.0.0-track05.xdelta', 'Tiny-EN-1.0.0-volume-iso.xdelta', 'VERSION', 'CHANGELOG.md', 'LICENSES')),
          'release folder: %s' % names)
    check('patcher' not in names, 'no patcher/ folder: apply_patch.py is a single file')
    check(get(os.path.join(out, 'CHANGELOG.md')) == CHANGELOG_TEXT, 'the changelog is bundled unchanged')
    check(sorted(os.listdir(os.path.join(out, 'LICENSES'))) == ['CC-BY-SA-4.0.txt', 'GPL-3.0-or-later.txt'],
          'the licence texts are bundled in LICENSES/')
    sums = get(os.path.join(out, 'SHA256SUMS')).decode()
    check('  CHANGELOG.md' in sums and '  LICENSES/CC-BY-SA-4.0.txt' in sums, 'SHA256SUMS covers CHANGELOG.md and LICENSES/')
    nt = get(os.path.join(out, 'NOTICE.txt')).decode()
    check('CC-BY-SA-4.0' in nt and 'NOT licensed by this project' in nt, 'NOTICE.txt names CC-BY-SA-4.0 and the game-data caveat')
    rd = get(os.path.join(out, 'README.md')).decode()
    check('CHANGELOG.md' in rd and 'CC-BY-SA-4.0' in rd and 'No original Sega pixels' in rd,
          'README.md mentions the changelog, CC-BY-SA-4.0 and that no original Sega pixels are distributed')
    check(json.loads(get(os.path.join(out, 'MANIFEST.json')).decode())['bundle'] == {'changelog': True, 'licenses': ['CC-BY-SA-4.0.txt', 'GPL-3.0-or-later.txt']},
          'manifest records the bundled changelog and licences')
    rc, text = run_apply(os.path.join(out, 'verify_dist.py'))
    check(rc == 0 and 'CHANGELOG.md has a section for 1.0.0' in text and 'LICENSES/CC-BY-SA-4.0.txt' in text, 'verify_dist: changelog and licences are checked (exit %d)' % rc)
    try:
        build_release(base, 'nochl', src_users, new_users, changelog_text=b'# Changelog\n\n## [Unreleased]\n')
        refused = ''
    except SystemExit as e:
        refused = str(e)
    check('has no section' in refused, 'a release whose version has no changelog section is refused')
    check(get(os.path.join(out, 'TRANSLATORS_NOTES.md')) == NOTES_TEXT, 'the translators notes are bundled unchanged')
    check(not any('track01' in x or 'track02' in x or 'track04' in x for x in names), 'no patch files for unchanged tracks')
    if x3:
        check(man['tracks']['3']['patch']['checks']['xdelta3'] == 'passed', 'xdelta3 cross-check passed inside produce()')
    m2 = json.loads(get(os.path.join(out, 'MANIFEST.json')).decode())
    check(m2['build_date'] == '2026-01-02' and m2['git_commit'] is None and m2['version'] == '1.0.0',
          'manifest has version, date from the argument, git commit null')
    for w in ('Redump', 'xdelta3 -d', 'apply_patch.py', 'SHA-1', 'track03.bin', '## 8. Known issues', '## 9. Credits', '## 10. Reporting problems',
              'Flycast emulator only', 'No original Sega pixels'):
        check(w in get(os.path.join(out, 'README.md')).decode(), 'README.md mentions %s' % w)
    patcher = os.path.join(out, 'apply_patch.py')

    def same_tracks(dirname, naming):
        for n in range(1, 6):
            name = TINY['tracks'][n]['redump_name' if naming == 'redump' else 'gdi_name']
            if get(os.path.join(dirname, name)) != built_tr[n]:
                return False
        return True

    for sheet, naming in (('cue', 'redump'), ('gdi', 'gdi')):
        d = os.path.join(base, 'player_' + sheet)
        p = write_tiny(d, src_tr, naming, sheet)
        before = {f: get(os.path.join(d, f)) for f in os.listdir(d)}
        rc, text = run_apply(patcher, p, '--verify')
        check(rc == 0 and 'unpatched disc' in text, '%s: --verify says original (exit %d)' % (sheet, rc))
        rc, text = run_apply(patcher, p)
        outdir = os.path.join(d, os.path.splitext(os.path.basename(p))[0] + ' (Tiny-EN)')
        check(rc == 0 and os.path.isdir(outdir), '%s: apply_patch.py succeeded, folder "%s"' % (sheet, os.path.basename(outdir)))
        check(same_tracks(outdir, naming), '%s: all 5 output tracks byte-equal to the built tracks' % sheet)
        check(get(os.path.join(outdir, os.path.basename(p))) == get(p), '%s: sheet copied unchanged' % sheet)
        check(before == {f: get(os.path.join(d, f)) for f in before}, '%s: source files untouched' % sheet)
        rc, text = run_apply(patcher, os.path.join(outdir, os.path.basename(p)), '--verify')
        check(rc == 0 and 'already patched' in text, '%s: --verify on the result says already patched' % sheet)
        rc, text = run_apply(patcher, os.path.join(outdir, os.path.basename(p)))
        check(rc == 0 and 'already patched' in text and not os.path.exists(os.path.join(outdir, os.path.basename(p)) + ' (Tiny-EN)'),
              '%s: patching a patched disc is refused politely' % sheet)
        rc, text = run_apply(patcher, p)
        check(rc == 1 and 'already holds a copy' in text, '%s: second run does not overwrite without --overwrite' % sheet)
        rc, text = run_apply(patcher, p, '--overwrite', '--link')
        check(rc == 0 and same_tracks(outdir, naming), '%s: --overwrite --link works' % sheet)
        rc, text = run_apply(patcher, p, '--out', d)
        check(rc == 1 and 'must not be the folder' in text, '%s: output folder equal to the source folder refused' % sheet)
        # the other route: cook to the volume ISO, patch it, rebuild the raw tracks (EDC/ECC) from it
        io_dir = os.path.join(base, 'isoroute_' + sheet)
        rc, text = run_apply(patcher, p, '--method', 'iso', '--out', io_dir)
        check(rc == 0 and same_tracks(io_dir, naming), '%s: --method iso (cook, patch, rebuild raw tracks) is byte-equal to the built tracks' % sheet)
        check(not [f for f in os.listdir(io_dir) if f.endswith('.tmp') or f.endswith('.partial')], '%s: no temporary files left' % sheet)
        to_iso = os.path.join(base, 'to_iso_%s.iso' % sheet)
        rc, text = run_apply(patcher, p, '--to', 'iso', '--out', to_iso)
        check(rc == 0 and get(to_iso) == get(os.path.join(base, 'a_work', 'b.iso')), '%s: --to iso gives the patched volume ISO' % sheet)
        check(not os.path.exists(to_iso + '.cooked.tmp'), '%s: --to iso leaves no temporary file' % sheet)
        # wrong dump: a changed track differs
        bad = os.path.join(base, 'bad_' + sheet)
        shutil.copytree(d, bad, ignore=shutil.ignore_patterns('* (Tiny-EN)'))
        t3 = os.path.join(bad, TINY['tracks'][3]['redump_name' if naming == 'redump' else 'gdi_name'])
        b = bytearray(get(t3))
        b[3000] ^= 1
        put(t3, bytes(b))
        rc, text = run_apply(patcher, os.path.join(bad, os.path.basename(p)))
        check(rc == 1 and 'REQUIRED' in text and 'Nothing was written' in text
              and not os.path.exists(os.path.join(bad, os.path.splitext(os.path.basename(p))[0] + ' (Tiny-EN)')),
              '%s: a corrupt track 3 is refused with a message, nothing written' % sheet)
        # unchanged track differs: only a warning
        warn = os.path.join(base, 'warn_' + sheet)
        shutil.copytree(d, warn, ignore=shutil.ignore_patterns('* (Tiny-EN)'))
        t4 = os.path.join(warn, TINY['tracks'][4]['redump_name' if naming == 'redump' else 'gdi_name'])
        put(t4, get(t4)[:-2352])
        rc, text = run_apply(patcher, os.path.join(warn, os.path.basename(p)))
        wout = os.path.join(warn, os.path.splitext(os.path.basename(p))[0] + ' (Tiny-EN)')
        check(rc == 0 and 'not changed by this patch' in text and os.path.isdir(wout),
              '%s: a differing UNCHANGED track only warns, patch still applied' % sheet)
    # volume iso
    d = os.path.join(base, 'player_iso')
    os.makedirs(d)
    iso = os.path.join(d, 'game.iso')
    shutil.copy(os.path.join(base, 'a_work', 's.iso'), iso)
    rc, text = run_apply(patcher, iso, '--verify')
    check(rc == 0 and 'unpatched volume ISO' in text, 'iso: --verify says original')
    rc, text = run_apply(patcher, iso)
    outp = os.path.join(d, 'game (Tiny-EN).iso')
    check(rc == 0 and os.path.exists(outp) and get(outp) == get(os.path.join(base, 'a_work', 'b.iso')),
          'iso: patched volume ISO byte-equal to the exported built disc')
    check(get(iso) == get(os.path.join(base, 'a_work', 's.iso')), 'iso: source untouched')
    rc, text = run_apply(patcher, outp, '--verify')
    check(rc == 0 and 'already patched' in text, 'iso: --verify on the result says already patched')
    bad = os.path.join(d, 'bad.iso')
    b = bytearray(get(iso))
    b[40000] ^= 1
    put(bad, bytes(b))
    rc, text = run_apply(patcher, bad)
    check(rc == 1 and 'volume ISO' in text and not os.path.exists(os.path.join(d, 'bad (Tiny-EN).iso')),
          'iso: a modified ISO is refused, nothing written')
    # the ISO patch really encodes the cooked change: also produce the same via vcdiff.py command line
    # empty release: nothing changed
    out2, man2, src_tr2, _ = build_release(base, 'e', src_users, src_users, x3=None)
    check(not any(man2['tracks'][n]['changed'] for n in man2['tracks']) and not man2['volume_iso']['changed'],
          'empty release: nothing changed, no patches')
    check(not [x for x in os.listdir(out2) if x.endswith('.xdelta')], 'empty release has no .xdelta files')
    d = os.path.join(base, 'player_empty')
    p = write_tiny(d, src_tr2, 'redump', 'cue')
    rc, text = run_apply(os.path.join(out2, 'apply_patch.py'), p)
    check(rc == 0 and 'changes no track' in text, 'empty release: apply_patch.py says nothing to do')
    # skeptic additions: a damaged / missing patch is found before anything is written; verify_dist flags stray files
    for what in ('damaged', 'missing'):
        dd = os.path.join(base, 'dmg_' + what)
        shutil.copytree(out, dd)
        pf = os.path.join(dd, 'Tiny-EN-1.0.0-track05.xdelta')
        if what == 'damaged':
            put(pf, get(pf)[:-5])
        else:
            os.remove(pf)
        pd = os.path.join(base, 'player_dmg_' + what)
        pp = write_tiny(pd, src_tr, 'redump', 'cue')
        for meth in ('raw', 'iso'):
            if what == 'missing' and meth == 'iso':
                continue                                     # the ISO route does not need the raw track patch
            rc, text = run_apply(os.path.join(dd, 'apply_patch.py'), pp, '--method', meth)
            if meth == 'iso' and what == 'damaged':
                check(rc == 0, 'iso route: a damaged RAW patch is not needed (exit %d)' % rc)
                shutil.rmtree(os.path.join(pd, os.path.splitext(os.path.basename(pp))[0] + ' (Tiny-EN)'), ignore_errors=True)
                continue
            leftovers = [f for f in os.listdir(pd) if f.endswith('(Tiny-EN)')]
            check(rc == 1 and ('damaged' in text or 'missing' in text) and not leftovers,
                  '%s raw patch: refused (exit %d), no output folder left behind %s' % (what, rc, leftovers))
    ds = os.path.join(base, 'stray')
    shutil.copytree(out, ds)
    put(os.path.join(ds, 'stray.txt'), b'x')
    rc, text = run_apply(os.path.join(ds, 'verify_dist.py'))
    check(rc == 1 and 'no file outside SHA256SUMS' in text, 'verify_dist: a file outside SHA256SUMS fails the folder check')
    # zip + sums
    z = R.zip_folder(out, '2026-01-02')
    check(os.path.exists(z) and os.path.exists(z + '.sha256'), 'zip and .zip.sha256 written')
    lines = get(os.path.join(out, 'SHA256SUMS')).decode().splitlines()
    ok = all(DF.hash_file(os.path.join(out, l.split('  ', 1)[1]))['sha256'] == l.split('  ', 1)[0] for l in lines)
    check(ok and len(lines) >= 8, 'SHA256SUMS verifies (%d files)' % len(lines))
    z2 = R.zip_folder(out, '2026-01-02')
    check(get(z) == get(z2), 'the zip is reproducible (entry dates come from --date)')


# ------------------------------------------------------------------ 4b
def test_rebuild_and_fallbacks():
    log('--- 4b: sector codec, forced sectors, other dumps, placeholder notes')
    import bincue2iso as BC
    rng = random.Random(11)
    ok = True
    for lba in (0, 7, 45000, 56890, 549149):
        u = bytes(rng.getrandbits(8) for _ in range(2048))
        ok &= BC.encode_sector(lba, u) == D.encode_sector(lba, u)
    check(ok, 'bincue2iso.encode_sector == discbuild.encode_sector (EDC, ECC, header) on random sectors')
    check(BC.encode_sector(3, bytes(2048)) == D.encode_sector(3, bytes(2048)), 'zero user data encodes identically too')
    base = os.path.join(WORK, 'more')
    shutil.rmtree(base, ignore_errors=True)
    src_users = make_tiny(rng)
    new_users = {k: (list(v) if isinstance(v, list) else v) for k, v in src_users.items()}
    new_users['u3'][5] = bytes(rng.getrandbits(8) for _ in range(2048))

    # a built track in which an all-zero original sector (track 5 pregap) was rewritten as a real Mode 1 sector
    def tweak(tr):
        t5 = bytearray(tr[5])
        t5[2 * 2352:3 * 2352] = D.encode_sector(127, bytes(2048))
        tr[5] = bytes(t5)
    out, man, src_tr, built_tr = build_release(base, 'f', src_users, new_users, tweak=tweak)
    check(man['raw_rebuild']['5'] == {'encode': [[2, 1]], 'sectors': 25}, 'compute_rebuild: the rewritten zero sector is listed as a forced run (%s)' % man['raw_rebuild'].get('5'))
    patcher = os.path.join(out, 'apply_patch.py')
    d = os.path.join(base, 'player')
    p = write_tiny(d, src_tr, 'redump', 'cue')
    for label, extra in (('raw route', []), ('iso route', ['--method', 'iso'])):
        o = os.path.join(base, 'o_' + label.split()[0])
        rc, text = run_apply(patcher, p, '--out', o, *extra)
        same = rc == 0 and all(get(os.path.join(o, TINY['tracks'][n]['redump_name'])) == built_tr[n] for n in range(1, 6))
        check(same, 'forced sector: %s reproduces the built tracks byte for byte' % label)
    # another dump of the same game data: a damaged EDC in track 3 (raw differs, user data equal)
    odd = os.path.join(base, 'odd')
    shutil.copytree(d, odd)
    t3 = os.path.join(odd, TINY['tracks'][3]['redump_name'])
    b = bytearray(get(t3))
    b[2 * 2352 + 2064 + 1] ^= 0x55
    put(t3, bytes(b))
    rc, text = run_apply(patcher, os.path.join(odd, 'tiny.cue'), '--out', os.path.join(base, 'o_odd'))
    check(rc == 0 and 'game data matches' in text, 'a dump whose raw track differs but whose game data is the same is patched through the ISO')
    t3o = get(os.path.join(base, 'o_odd', TINY['tracks'][3]['redump_name']))
    check(R.diff_sector_runs(os.path.join(base, 'o_odd', TINY['tracks'][3]['redump_name']),
                             os.path.join(base, 'f_work', 'b3.bin')) == [(2, 1)],
          'the result differs from the built track only in the sector that was damaged in the player\'s dump (kept as it was)')
    rc, text = run_apply(patcher, os.path.join(odd, 'tiny.cue'), '--verify')
    check(rc == 0 and 'ISO route' in text, '--verify recognises the other dump as patchable through the ISO route')
    # different game data: refused
    wrong = os.path.join(base, 'wrong')
    shutil.copytree(d, wrong)
    t3 = os.path.join(wrong, TINY['tracks'][3]['redump_name'])
    b = bytearray(get(t3))
    b[5 * 2352 + 20] ^= 0x55
    put(t3, bytes(b))
    rc, text = run_apply(patcher, os.path.join(wrong, 'tiny.cue'), '--out', os.path.join(base, 'o_wrong'))
    check(rc == 1 and 'different game data' in text and not os.path.exists(os.path.join(base, 'o_wrong')), 'different game data: refused, nothing written')
    # a bundle without the raw track patches: BIN/CUE and GDI players go through the volume ISO
    out_n, man_n, src_tr_n, built_tr_n = build_release(base, 'n', src_users, new_users, raw=False)
    check(not any('track0' in x for x in os.listdir(out_n)) and man_n['raw_patches'] is False
          and 'patch' not in man_n['tracks']['3'] and man_n['volume_iso']['patch']['size'] > 0,
          'no-raw-patches bundle: only the volume-ISO patch is shipped')
    pn = os.path.join(out_n, 'apply_patch.py')
    dn = os.path.join(base, 'player_n')
    sheet_n = write_tiny(dn, src_tr_n, 'redump', 'cue')
    rc, text = run_apply(pn, sheet_n, '--out', os.path.join(base, 'o_n'))
    check(rc == 0 and 'volume ISO' in text and all(get(os.path.join(base, 'o_n', TINY['tracks'][n]['redump_name'])) == built_tr_n[n] for n in range(1, 6)),
          'no-raw-patches bundle: a BIN/CUE dump is patched through the ISO, tracks byte-equal to the built ones')
    rc, text = run_apply(pn, sheet_n, '--method', 'raw', '--out', os.path.join(base, 'o_n2'))
    check(rc == 1 and 'no raw track patches' in text, 'no-raw-patches bundle: --method raw is refused with a message')
    check('none: the volume-ISO patch is used' in get(os.path.join(out_n, 'README.md')).decode(), 'README.md of that bundle says so')
    # placeholder notes
    try:
        build_release(base, 'p', src_users, new_users, notes_text=b'# Notes\nPLACEHOLDER\n')
        check(False, 'a PLACEHOLDER notes file must fail the bundle')
    except SystemExit as e:
        check('PLACEHOLDER' in str(e), 'a notes file with the marker PLACEHOLDER fails the bundle (%s)' % str(e)[:60])
    out3, man3, _, _ = build_release(base, 'q', src_users, new_users, notes_text=b'# Notes\nPLACEHOLDER\n', allow=True)
    check(os.path.exists(os.path.join(out3, 'TRANSLATORS_NOTES.md')), '--allow-placeholder bundles it anyway')
    try:
        R.check_notes(os.path.join(base, 'no_such_notes.md'), False)
        check(False, 'a missing notes file must fail')
    except SystemExit as e:
        check('do not exist' in str(e), 'a missing translators notes file fails the bundle')
    cfg = R.load_config()
    check(os.path.isfile(R.notes_path(cfg)), 'release.toml [bundle] translators_notes points to an existing file (%s)' % R.notes_path(cfg))
    # the dev tables of release.toml are complete and labelled
    for name, tab in (cfg.get('dev') or {}).items():
        check(all(k in tab and all(h in tab[k] for h in R.HASH_KEYS) for k in ['track%d' % n for n in range(1, 6)] + ['volume_iso'])
              and 'development' in tab.get('note', ''), '[dev.%s] in release.toml is complete and labelled as a development record' % name)


# ------------------------------------------------------------------ 5
def test_py38():
    log('--- 5: python 3.8 syntax of the shipped files')
    for n in ('apply_patch.py', 'vcdiff.py', 'discformat.py', 'bincue2iso.py', 'verify_dist.py'):
        with open(os.path.join(HERE, n), encoding='utf8') as f:
            ast.parse(f.read(), feature_version=(3, 8))
        check(True, '%s parses as Python 3.8' % n)
    for n in ('apply_patch.py', 'vcdiff.py', 'verify_dist.py'):
        with open(os.path.join(HERE, n), encoding='utf8') as f:
            head = f.read(200)
        check('SPDX-License-Identifier: GPL-3.0-or-later' in head, '%s keeps the SPDX/copyright header' % n)
    ast.parse(R.single_file_apply(), feature_version=(3, 8))
    check(True, 'the generated single-file apply_patch.py parses as Python 3.8')


# ------------------------------------------------------------------ 6
GUIDE_HEADINGS = ('What this is', 'Applying the patch', 'Money: oku and man', 'Names', 'Places and club names',
                  'Ranks, counters, positions', 'The name-entry screen', 'Known rough spots', 'Build options',
                  'Credits and licence', 'FAQ')


def test_version_and_licences(guide):
    """Version single source, root changelog (Keep a Changelog), licence texts and the REUSE map."""
    import re
    log('--- 6b: version, changelog, licences')
    ver = R.read_version()
    check(R.SEMVER.match(ver) and '-dev' not in ver, 'tools/VERSION %s is a semantic version, not a dev version' % ver)
    # the official SemVer 2.0.0 grammar: valid examples of semver.org, and the invalid ones the old loose pattern let through
    good = ['0.0.4', '1.2.3', '10.20.30', '1.1.2-prerelease+meta', '1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-0.3.7',
            '1.0.0-x.7.z.92', '1.0.0-x-y-z.--', '1.0.0-alpha+001', '1.0.0+20130313144700', '1.0.0-beta+exp.sha.5114f85',
            '0.1.0-beta.1', '1.0.0-rc.1', '1.0.0-0A.is.legal', '1.0.0-alpha-a.b-c-somethinglong+build.1-aef.1-its-okay']
    bad = ['1', '1.2', '1.2.3.4', '01.1.1', '1.01.1', '1.1.01', '1.2.3-', '1.2.3-.', '1.2.3-a..b', '1.2.3-01', '1.0.0-alpha.01',
           '1.2.3-beta.', '1.2.3-.beta', '1.2.3+', '1.2.3+a..b', '1.2.3+.b', '1.2.3-a_b', '1.2.3-beta+x_y', '1.0.0-', 'v1.2.3',
           '1.2.3\n', '1.2.3-beta.1\n']
    check(all(R.SEMVER.match(v) for v in good), 'SEMVER accepts the valid SemVer 2.0.0 examples')
    check(not [v for v in bad if R.SEMVER.match(v)],
          'SEMVER rejects leading-zero numeric prerelease ids, empty identifiers, trailing newline: %s' % [v for v in bad if R.SEMVER.match(v)])
    check(R.SEMVER.match('0.1.0-beta.1').group(4) == 'beta.1' and R.SEMVER.match('1.0.0-rc.1+b.2').group(5) == 'b.2',
          'SEMVER group 4 is the prerelease, group 5 the build metadata')
    # bundle files must carry no absolute local paths
    sample = 'cue: %s\\build\\release\\disc\\x.cue\n$ %s -I tool.py\nelse C:\\Users\\Someone\\Elsewhere\\f.txt and /c/Users/Someone/g\n' % (R.ROOT, sys.executable)
    scrubbed = R.scrub_paths(sample)
    check(not R.LOCAL_PATH_RE.search(scrubbed) and 'build\\release\\disc\\x.cue' in scrubbed and '$ python -I tool.py' in scrubbed,
          'scrub_paths makes repo paths relative, the interpreter "python", other home paths "<home>": %r' % scrubbed)
    cl = get(os.path.join(ROOT, 'CHANGELOG.md')).decode('utf-8')
    check('keepachangelog.com/en/1.1.0' in cl and 'semver.org/spec/v2.0.0' in cl, 'CHANGELOG.md names Keep a Changelog 1.1.0 and SemVer 2.0.0')
    heads = re.findall(r'^## \[([^\]]+)\]', cl, re.M)
    check(heads == ['Unreleased', ver], 'CHANGELOG.md: [Unreleased] on top, then the current version %s (%s)' % (ver, heads))
    check(re.search(r'^## \[%s\] - \d{4}-\d{2}-\d{2}\s*$' % re.escape(ver), cl, re.M) is not None, 'CHANGELOG.md: %s has an ISO date' % ver)
    sec = cl.split('## [%s]' % ver)[1].split('[Unreleased]:')[0]
    for h in ('### Added', '### Known issues'):
        check(h in sec, 'CHANGELOG.md %s has %s' % (ver, h))
    kac = set(x.strip() for x in re.findall(r'^### (.+)$', cl, re.M))
    check(kac <= {'Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Security', 'Known issues'},
          'CHANGELOG.md uses only the Keep a Changelog headings (plus Known issues): %s' % sorted(kac))
    check(R.changelog_section(cl, ver, 'Known issues'), 'the Known issues of %s are bullet lines the bundle README can quote' % ver)
    check('honorifics' in sec.lower() and 'name order' in sec.lower() and 'Planned for 0.2.0' in sec,
          'CHANGELOG.md: optional honorifics and name order are noted as planned for 0.2.0')
    base = 'https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN'
    check('[%s]: %s/releases/tag/v%s' % (ver, base, ver) in cl and '[Unreleased]: %s/compare/v%s...HEAD' % (base, ver) in cl,
          'CHANGELOG.md has the compare / release links')
    check('CHANGELOG.md' in get(os.path.join(ROOT, 'doc', 'CHANGELOG.md')).decode(), 'doc/CHANGELOG.md points to the root changelog')
    check(R.read_version() == ver and os.path.basename(os.path.join(ROOT, 'dist', '%s-%s' % (R.PROJECT, ver))) == 'SakaTsuku2-EN-' + ver,
          'the bundle name is SakaTsuku2-EN-%s' % ver)
    cfg = R.load_config()
    check(os.path.isfile(R.bundle_path(cfg, 'changelog')) and os.path.isdir(R.bundle_path(cfg, 'licenses_dir')),
          'release.toml [bundle] points to the changelog and the LICENSES folder')
    ccp = os.path.join(ROOT, 'LICENSES', 'CC-BY-SA-4.0.txt')
    cc = get(ccp).decode('utf-8')
    check(cc.startswith('Creative Commons Attribution-ShareAlike 4.0 International')
          and 'Attribution-ShareAlike 4.0 International Public License' in cc and all(('Section %d' % i) in cc for i in range(1, 9)),
          'LICENSES/CC-BY-SA-4.0.txt has the CC BY-SA 4.0 legal code (sections 1-8)')
    check('GNU GENERAL PUBLIC LICENSE' in get(os.path.join(ROOT, 'LICENSES', 'GPL-3.0-or-later.txt')).decode()
          and get(os.path.join(ROOT, 'LICENSES', 'GPL-3.0-or-later.txt')) == get(os.path.join(ROOT, 'LICENSE')),
          'LICENSES/GPL-3.0-or-later.txt equals LICENSE')
    import tomllib
    reuse = tomllib.loads(get(os.path.join(ROOT, 'REUSE.toml')).decode('utf-8'))
    ann = {tuple(a['path'] if isinstance(a['path'], list) else [a['path']]): a['SPDX-License-Identifier'] for a in reuse['annotations']}
    flat = {p: lic for k, lic in ann.items() for p in k}
    check(flat['**'] == 'GPL-3.0-or-later', 'REUSE.toml: default is GPL-3.0-or-later (tooling, scripts, tests)')
    for p in ('README.md', 'doc/**', 'docs/**', 'translation/*.jsonl', 'l10n/textures/**'):
        check('CC-BY-SA-4.0' in (flat.get(p) or ''), 'REUSE.toml: %s is CC-BY-SA-4.0 (alone, or with LicenseRef-Game-Content where the file also holds game material)' % p)
    check('LicenseRef-Game-Content' in flat.values() and os.path.isfile(os.path.join(ROOT, 'LICENSES', 'LicenseRef-Game-Content.txt')),
          'REUSE.toml marks original-game pictures as not licensed (LicenseRef-Game-Content)')
    check('CC-BY-SA' in guide and 'no original Sega pixels' in guide and 'not licensed' in guide.replace('\n', ' '),
          'the guide states CC-BY-SA, no original Sega pixels, and that the game is not licensed by the project')
    rl = get(os.path.join(ROOT, 'README.md')).decode('utf-8')
    check('CC-BY-SA-4.0' in rl and 'GPL-3.0-or-later' in rl and 'original Sega pixels' in rl, 'README.md has the licence statement')


def test_guide():
    """The real translators' notes (doc/TRANSLATORS_NOTES.md, written by the guide owner) are valid and are bundled."""
    import re
    log('--- 6: the translators notes / player guide')
    cfg = R.load_config()
    path = R.notes_path(cfg)
    text = get(path).decode('utf-8')
    check('PLACEHOLDER' not in text, 'the real guide has no PLACEHOLDER marker (release.py would refuse it)')
    heads = re.findall(r'^## \d+\. (.+)$', text, re.M)
    for h in GUIDE_HEADINGS:
        check(any(x.startswith(h) for x in heads), 'guide has the section "%s"' % h)
    for kw in ('oku', 'man', 'kyu', 'dan', 'GPL-3.0-or-later', 'xdelta', 'nearest-neighbour', 'apply_patch.py', 'no original Sega pixels',
               '--money-style', '--refit', '--prop-scale', '--hw-relocate', '--club-guard'):
        check(kw in text, 'guide mentions %s' % kw)
    # the SHA-1 table of the original disc equals release.toml
    for key in ('track1', 'track2', 'track3', 'track4', 'track5', 'volume_iso'):
        sha = R.recorded(cfg, key)['sha1']
        check('`%s`' % sha in text, 'guide quotes the SHA-1 of %s from release.toml' % key)
    # every worked money example "`X oku Y man` | N yen" is arithmetically right
    n = 0
    for m in re.finditer(r'^\| `([^`]+)` \| (-?[\d,]+) yen \|', text, re.M):
        s, yen = m.group(1), int(m.group(2).replace(',', ''))
        oku = re.search(r'(\d+) oku', s)
        man = re.search(r'(\d+) man', s)
        want = (int(oku.group(1)) * 10 ** 8 if oku else 0) + (int(man.group(1)) * 10 ** 4 if man else 0)
        check(want == yen, 'money example "%s" = %s yen' % (s, m.group(2)))
        n += 1
    check(n >= 8, 'guide has %d worked money examples' % n)
    test_version_and_licences(text)
    # bundled byte for byte into a (tiny) release, with the placeholder check ON
    base = os.path.join(WORK, 'guide')
    shutil.rmtree(base, ignore_errors=True)
    rng = random.Random(7)
    src_users = make_tiny(rng)
    new_users = {k: (list(v) if isinstance(v, list) else v) for k, v in src_users.items()}
    new_users['u3'][5] = bytes(rng.getrandbits(8) for _ in range(2048))
    out, man, _, _ = build_release(base, 'g', src_users, new_users, notes_text=text.encode('utf-8'))
    check(get(os.path.join(out, 'TRANSLATORS_NOTES.md')) == text.encode('utf-8'), 'the real guide is bundled unchanged as TRANSLATORS_NOTES.md')
    check('TRANSLATORS_NOTES.md' in get(os.path.join(out, 'README.md')).decode(), 'README.md points to TRANSLATORS_NOTES.md')
    check('TRANSLATORS_NOTES.md' in get(os.path.join(out, 'SHA256SUMS')).decode(), 'SHA256SUMS covers the guide')


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    test_repo_facts()
    test_detect()
    test_export()
    test_apply()
    test_rebuild_and_fallbacks()
    test_py38()
    test_guide()
    ok = sum(1 for c, _ in RESULTS if c)
    log('RESULT: %d checks passed, %d failed' % (ok, len(RESULTS) - ok))
    shutil.rmtree(WORK, ignore_errors=True)
    return 0 if ok == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
