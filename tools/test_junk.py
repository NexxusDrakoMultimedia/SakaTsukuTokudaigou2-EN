"""Junk guards: no orphan record with placeholder English (docs/hang-investigation.md s0) and no pointer / data / code record
(is_binary_record, s9: GAME.BIN#82138 reset the console on a goal) may be applied, and the database holds none.
run: python -I -X utf8 tools/test_junk.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_patch  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name)
    if not cond:
        fails += 1


check('placeholder "-" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': '-'}))
check('placeholder "Bow" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': 'Bow'}))
check('"????" is junk', build_patch.is_junk_orphan({'orphan': True, 'en': '????'}))
check('real word is not junk', not build_patch.is_junk_orphan({'orphan': True, 'en': 'Chat'}))
check('pointer record "-" is not junk', not build_patch.is_junk_orphan({'en': '-'}))
check('blank en is not junk', not build_patch.is_junk_orphan({'orphan': True, 'en': ''}))

bad = []
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        if build_patch.is_junk_orphan(r):
            bad.append(r['id'])
check('translation/*.jsonl has no junk orphan record (%d found)' % len(bad), not bad)
# ---- is_binary_record: pointer records whose original bytes are machine data (docs/hang-investigation.md s9) ----
import textdb  # noqa: E402

SRCS = build_patch.overlay_sources()
IMG = {}


def image(src):
    if src not in IMG:
        IMG[src] = textdb.load_image(src)
    return IMG[src]


class Img:
    """synthetic image: data at base 0x8c010000"""

    def __init__(self, data):
        self.data, self.base = data, 0x8c010000


def ptr(off):
    return (0x8c010000 + off).to_bytes(4, 'little')


def rec(src, off, en):
    return {'id': '%s#%x' % (src, off), 'en': en}


def find_orig(img, jp):
    """offset of a NUL-delimited original string (cp932) in an image, or -1"""
    b = b'\0' + jp.encode('cp932') + b'\0'
    i = img.data.find(b)
    return i + 1 if i >= 0 else -1


g = image('FLOW_PRG/GAME.BIN')
a = image('FLOW_PRG/AUTOSAVE.BIN')
check('real GAME.BIN#82138 over a script pointer, en "---": binary', build_patch.is_binary_record(rec('FLOW_PRG/GAME.BIN', 0x82138, '---'), g))
check('real GAME.BIN#11a2c8 (palette), en "---": binary', build_patch.is_binary_record(rec('FLOW_PRG/GAME.BIN', 0x11a2c8, '---'), g))
check('real AUTOSAVE.BIN#3353c (pointer table, real English): binary',
      build_patch.is_binary_record(rec('FLOW_PRG/AUTOSAVE.BIN', 0x3353c, '<3C> %2d/%2d %2d:%02d'), a))
check('blank en is never binary', not build_patch.is_binary_record(rec('FLOW_PRG/GAME.BIN', 0x82138, ''), g))
check('place name over a pointer-looking 4 bytes is not binary (AUTOSAVE.BIN#696d4)',
      not build_patch.is_binary_record(rec('FLOW_PRG/AUTOSAVE.BIN', 0x696d4, 'Kanto'), a))
off = find_orig(g, '\uff0d')        # the full-width hyphen-minus: a genuine separator, no kanji
check('genuine "-" separator record over a full-width dash is not binary',
      off > 0 and not build_patch.is_binary_record(rec('FLOW_PRG/GAME.BIN', off, '-'), g))
# a real ellipsis record (three middle dots and a full stop in the original), translated '...'
check('"..." over an ellipsis (MEETING.BIN#52d0e) is not binary',
      not build_patch.is_binary_record(rec('FLOW_PRG/MEETING.BIN', 0x52d0e, '...'), image('FLOW_PRG/MEETING.BIN')))
# synthetic originals
tab = ptr(0x121) + ptr(0x125) + b'text\0'
check('synthetic: two in-image pointers then text is binary', build_patch.is_binary_record(rec('X', 0, 'Date'), Img(tab + b'\0' * 512)))
one = ptr(0x121) + b'ab\0'
check('synthetic: one in-image word alone is not binary', not build_patch.is_binary_record(rec('X', 0, 'Date'), Img(one + b'\0' * 512)))
check('synthetic: ASCII original with "-" is not binary', not build_patch.is_binary_record(rec('X', 0, '-'), Img(b'ab\0' + b'\0' * 64)))
check('synthetic: kanji original over "-" is binary', build_patch.is_binary_record(rec('X', 0, '-'), Img('\u6fc6:\u7e4b'.encode('cp932') + b'\0' * 64)))
check('synthetic: kanji original over a real word is not binary',
      not build_patch.is_binary_record(rec('X', 0, 'Kanto'), Img('\u95a2\u6771'.encode('cp932') + b'\0' * 64)))

# the two records of the goal crash are blank and skip in both forms (the l10n form has the id without the file name)
CLASS = ['FLOW_PRG/GAME.BIN#82138', 'FLOW_PRG/GAME.BIN#11a2c8']
for d in ('translation', 'l10n'):
    for rid in CLASS:
        src, o = rid.rsplit('#', 1)
        rr = None
        for ln in open(os.path.join(ROOT, d, src.replace('/', '__') + '.jsonl'), encoding='utf-8'):
            j = json.loads(ln)
            if j.get('id') in (rid, o):
                rr = j
                break
        check('%s: %s is blank and skip' % (d, rid), rr is not None and not rr.get('en') and rr.get('skip') is True)

# whole database: no record with English is a binary record
bad = []
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        if not r.get('en'):
            continue
        src = r['id'].rsplit('#', 1)[0]
        if src in SRCS and build_patch.is_binary_record(r, image(src)):
            bad.append(r['id'])
check('translation/*.jsonl has no binary record with English (%d found: %s)' % (len(bad), ' '.join(bad[:5])), not bad)

print('FAILED %d' % fails if fails else 'all passed')
sys.exit(1 if fails else 0)
