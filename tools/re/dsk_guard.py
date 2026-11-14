"""dsk_guard: check that build_disc refuses to write over the source tracks.  write_track is stubbed so nothing can be written."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import discbuild as D   # noqa: E402


def boom(*a, **k):
    raise AssertionError('write_track reached: NO GUARD')


D.write_track = boom
try:
    D.build_disc({}, ROOT, 'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan)', ROOT)
    print('built?!')
except D.DiscError as e:
    print('refused:', e)
except AssertionError as e:
    print('FAIL', e)
