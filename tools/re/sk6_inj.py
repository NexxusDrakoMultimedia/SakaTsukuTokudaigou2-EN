"""sk6_inj: exact-policy injection check of the two header textures. sk6_inj.py"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject
for f, tid in (('FLOW_PRG/LOADBAR.BIN', '@1ec#0'), ('FLOW_PRG/YOUTH.BIN', '@36114#0')):
    pv = open(os.path.join(ROOT, 'translation', 'textures', *f.split('/'), tid + '.pvr'), 'rb').read()
    r = texinject.replace_texture(f, tid, pv, policy='exact')
    print(f, tid, 'OK', len(r))
