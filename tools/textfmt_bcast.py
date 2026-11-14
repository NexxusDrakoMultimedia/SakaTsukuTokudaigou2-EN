"""textfmt_bcast - transcript (subtitle) text of the voice clips in /BCAST/BCAST.BIN  (owner: text, prefix tx5).

BCAST.BIN (630 MB, 307,326 sectors from LBA 68002, not in extracted/) is a concatenation of ADPCM voice clips (the match
commentary, the studio announcer, the player-name callouts).  Every clip is ONE 2048-byte header sector followed by the audio:

    +0x00  "PCM FILE START  "                      16 bytes
    +0x10  clip name, NUL padded                  0x30  e.g. yh\\yh_end_aisa_0002.p04
    +0x40  "size:NNNNN"                            ASCII
    +0x50  "<start sector, 5 digits> - <audio sectors>"   ASCII
    +0x60  u32 LE offsets of the text segments (relative to the header start), terminated by 0   (up to 8, 0x60..0x7c)
    +0x80..  the segments: cp932 text, NUL terminated; segment i owns [off[i], off[i+1]) and the last one owns the rest of its
             64-byte line (see LAST_SLOT)
The game shows the segments one after the other as the subtitle while the clip plays (the commentary box of the match screen
and the attract demo): the Japanese on screen is exactly this text.  Nothing else on the disc holds it (PROVEN: cp932 search of
extracted/, build/unpacked/ and the whole BCAST.BIN gives the transcripts only here).

Record format (translation/BCAST__BCAST.BIN.jsonl, compact JSON lines like textdb):
    {"id":"BCAST/BCAST.BIN#<hex file offset of the segment>","ja":"...","en":"","max_bytes":N,"refs":null,
     "ctx":"clip yh\\\\yh_end_aisa_0002 seg 0/1 ...","fmt":"bcast"}
`max_bytes` = slot size including the NUL.  Records are written IN PLACE into the header sector (nothing moves, no sector is added):
`build_patch.do_bcast` re-reads the header from the original disc, checks that the segment still holds `ja` (else SKIPPED), checks
`len(en)+1 <= max_bytes` (else FAILED), pads with NUL and hands the 2048-byte sectors to discbuild as a sparse patch.

    python -I -X utf8 tools/textfmt_bcast.py stats                 # what is in the archive
    python -I -X utf8 tools/textfmt_bcast.py extract [--write]     # build the records (keeps existing en / skip by id)
"""
import collections
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gdrom                       # noqa: E402
import textfmt_common as C         # noqa: E402

SOURCE = 'BCAST/BCAST.BIN'
ISO_PATH = '/BCAST/BCAST.BIN'
BCAST_LBA = 68002                  # first sector of the file on the disc
BCAST_SECTORS = 307326
SECTOR = 2048
MAGIC = b'PCM FILE START  '
TABLE = 0x60
TEXT0 = 0x80
LAST_SLOT = 0x40                   # default room of the last segment when the next field is not another segment (see header_segments)
FMT = 'bcast'
JSONL = os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl')


def cstr(b):
    i = b.find(b'\0')
    return b if i < 0 else b[:i]


def header_segments(h):
    """-> (name, [(offset, slot_size, raw_bytes)]) of a 2048-byte header.  Offsets must be ascending, 4-aligned, within [0x80, 0x800)."""
    if h[:16] != MAGIC:
        raise ValueError('not a PCM header')
    name = cstr(h[0x10:0x40]).decode('ascii', 'replace')
    offs = []
    for i in range(TABLE, TEXT0, 4):
        v, = struct.unpack_from('<I', h, i)
        if v == 0:
            break
        offs.append(v)
    segs = []
    for k, o in enumerate(offs):
        if not TEXT0 <= o < SECTOR or (k and o <= offs[k - 1]):
            raise ValueError('bad segment table %r' % (offs,))
        nxt = offs[k + 1] if k + 1 < len(offs) else None
        if nxt is None:
            # last segment: runs to the end of its text, rounded up to the 16-byte grid, but never less than the room before
            # the next non-zero byte behind it (there is none: checked by `stats`)
            end = o
            while end < SECTOR and h[end]:
                end += 1
            slot = max(((end - o + 1 + 15) // 16) * 16, LAST_SLOT if (end - o + 1) > 16 else 16)
            nz = [j for j in range(end + 1, SECTOR) if h[j]]
            if nz:
                slot = min(slot, nz[0] - o)
                slot = max(slot, end - o + 1)
        else:
            slot = nxt - o
        segs.append((o, slot, cstr(h[o:o + slot])))
    return name, segs


def read_headers(disc_dir=None):
    """Scan the original BCAST.BIN: -> [(sector index inside the file, header bytes)]."""
    d = gdrom.Disc(disc_dir or ROOT)
    rows = []
    CH = 512
    for base in range(0, BCAST_SECTORS, CH):
        n = min(CH, BCAST_SECTORS - base)
        buf = d.read(BCAST_LBA + base, n * SECTOR)
        pos = 0
        while True:
            i = buf.find(MAGIC, pos)
            if i < 0:
                break
            pos = i + 1
            if i % SECTOR:
                continue
            rows.append((base + i // SECTOR, buf[i:i + SECTOR]))
    return rows


def read_header(disc, sector):
    return disc.read(BCAST_LBA + sector, SECTOR)


def file_offset(sector, seg_off):
    return sector * SECTOR + seg_off


CAP_COMMENTARY = 75                # 2 lines x 37 cells of GAME.BIN's own message engine (docs/text-sources.md, BCAST) + NUL
CAP_NAME = 16                      # a name callout: 15 characters + NUL (the Japanese slots are 16 bytes)
ALIGN = 16                         # re-packed segments start on the 16-byte grid of the original headers


def display_cap(folder, slot):
    """Display budget (bytes incl. NUL) of a segment: the record's max_bytes.  The slot of the original header is NOT the limit:
    a clip whose English does not fit its slots is re-laid out (apply_header)."""
    if folder == 'name':
        return max(CAP_NAME, slot)
    return CAP_COMMENTARY


def extract(rows):
    """-> list of record dicts (no en)."""
    out = []
    for sec, h in rows:
        name, segs = header_segments(h)
        stem = name.rsplit('.', 1)[0]
        folder = name.split('\\')[0]
        for k, (o, slot, raw) in enumerate(segs):
            if not raw:
                continue
            ja = C.decode_text(raw)
            out.append({'id': '%s#%x' % (SOURCE, file_offset(sec, o)), 'ja': ja, 'en': '', 'max_bytes': display_cap(folder, slot),
                        'refs': None, 'ctx': 'clip %s seg %d/%d slot %d' % (stem, k, len(segs), slot), 'fmt': FMT})
    return out


def read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def write_jsonl(path, recs):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    os.replace(tmp, path)


def merge_existing(new, old):
    """Keep en / skip of existing records with the same id and the same ja."""
    byid = {r['id']: r for r in old}
    for r in new:
        o = byid.get(r['id'])
        if o and o.get('ja') == r['ja']:
            for k in ('en', 'skip'):
                if o.get(k):
                    r[k] = o[k]
    return new


def apply_to_header(h, edits):
    """h: 2048-byte header; edits {segment offset: (ja_expected, en, max_bytes)}.
    Returns (new_header, bad, stale) with bad / stale = [(offset, reason)]: `stale` = the id no longer matches the header (SKIPPED),
    `bad` = the English cannot be written (FAILED: not cp932, contains a newline, over max_bytes, no room in the header).
    Untouched segments keep their bytes.  If every edited text fits the slot of its segment the edit is in place; otherwise the clip is
    re-laid out: the segments are packed one behind the other from +0x80 on the 16-byte grid and the offset table at +0x60 is
    rewritten (the game finds a segment through that table; the room is the whole rest of the sector, 1920 bytes)."""
    name, segs = header_segments(h)
    by = {o: (slot, raw) for o, slot, raw in segs}
    bad, stale = [], []
    final = {}
    for o, edit in edits.items():
        ja, en = edit[0], edit[1]
        cap = edit[2] if len(edit) > 2 else None
        if o not in by:
            stale.append((o, 'no segment at this offset (stale id)'))
            continue
        if C.decode_text(by[o][1]) != ja:
            stale.append((o, 'ja text differs from the header (stale database?)'))
            continue
        if '\n' in en:
            bad.append((o, 'newline in a subtitle (the message engine would draw it as a glyph)'))
            continue
        try:
            b = C.encode_text(en)
        except UnicodeEncodeError:
            bad.append((o, 'English not encodable in cp932'))
            continue
        if cap is not None and len(b) + 1 > cap:
            bad.append((o, 'English is %d bytes, budget %d (incl. NUL)' % (len(b), cap)))
            continue
        final[o] = b
    if not final:
        return h, bad, stale
    in_place = all(len(b) + 1 <= by[o][0] for o, b in final.items())
    new = bytearray(h)
    if in_place:
        for o, b in final.items():
            slot = by[o][0]
            new[o:o + slot] = b + b'\0' * (slot - len(b))
        return bytes(new), bad, stale
    texts = [final.get(o, raw) for o, slot, raw in segs]
    pos = TEXT0
    offs = []
    for t in texts:
        offs.append(pos)
        pos += ((len(t) + 1 + ALIGN - 1) // ALIGN) * ALIGN
    if pos > SECTOR or len(offs) > (TEXT0 - TABLE) // 4:
        for o in final:
            bad.append((o, 're-laid out clip needs %d bytes, the header has %d' % (pos - TEXT0, SECTOR - TEXT0)))
        return h, bad, stale
    new[TABLE:SECTOR] = bytes(SECTOR - TABLE)
    for i, (off, t) in enumerate(zip(offs, texts)):
        struct.pack_into('<I', new, TABLE + 4 * i, off)
        new[off:off + len(t)] = t
    return bytes(new), bad, stale


def stats(rows):
    nseg = collections.Counter()
    slots = collections.Counter()
    stray = 0
    folders = collections.Counter()
    for sec, h in rows:
        name, segs = header_segments(h)
        nseg[len(segs)] += 1
        folders[name.split('\\')[0]] += 1
        used = set()
        for o, slot, raw in segs:
            slots[slot] += 1
            used.update(range(o, o + slot))
        if any(h[j] for j in range(TEXT0, SECTOR) if j not in used):
            stray += 1
    print('clips', len(rows), 'folders', dict(folders))
    print('segments per clip', sorted(nseg.items()))
    print('slot sizes', sorted(slots.items()))
    print('headers with non-zero bytes outside the segments:', stray)


def main(argv):
    if not argv or argv[0] not in ('stats', 'extract'):
        print(__doc__)
        return 1
    rows = read_headers()
    if argv[0] == 'stats':
        stats(rows)
        return 0
    new = extract(rows)
    old = read_jsonl(JSONL) if os.path.exists(JSONL) else []
    new = merge_existing(new, old)
    print('records', len(new), 'with en', sum(1 for r in new if r.get('en')), 'distinct ja', len({r['ja'] for r in new}))
    if '--write' in argv:
        write_jsonl(JSONL, new)
        print('wrote', JSONL)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
