import sys, os
sys.path.insert(0, 'tools')
import texinject
base = 'build/art6/tex_only'
g = texinject.load_textures_dir(base, 'extracted')
for cont, d in sorted(g.items()):
    data = open(os.path.join('extracted', cont), 'rb').read()
    for tid, pvr in sorted(d.items()):
        try:
            texinject.replace_textures(data, {tid: pvr}, 'exact')
            print('OK  ', cont, tid)
        except Exception as e:
            print('FAIL', cont, tid, str(e)[:110])
