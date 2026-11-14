"""hsd: apply every translation/textures file whose id is '@hex#i' (embedded or tail tables) to its extracted container with the current
texinject and report stored ZSARC members whose CRC16 / header CRC would be stale, plus the game walk of those members.  Read-only; writes nothing.
usage: hsd_verify_all.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T
groups = T.load_textures_dir(os.path.join(ROOT, 'translation', 'textures'), os.path.join(ROOT, 'extracted'))
bad = 0
for cont in sorted(groups):
    ids = [t for t in groups[cont] if str(t).startswith('@')]
    if not ids:
        continue
    d = open(os.path.join(ROOT, 'extracted', *cont.split('/')), 'rb').read()
    new = d
    note = []
    for tid in sorted(ids):
        r = T.inject(new, tid, groups[cont][tid])
        new = r.data
        if r.info.get('member_crc_refreshed'):
            note.append('%s -> member %r refreshed' % (tid, r.info['member_crc_refreshed']))
    stale = T.stale_stored_members(d, new)
    bad += len(stale)
    print('%-28s %-22s stale=%s %s' % (cont, ','.join(sorted(ids)), stale, '; '.join(note)))
print('stale members total', bad)
