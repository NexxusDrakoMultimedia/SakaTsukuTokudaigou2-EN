import os, shutil
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
mine = [('ETC_DATA/N_ENTRY.DAT', 'pvr.tbd#0'), ('ETC_DATA/PASSWD.TBD', '#0'), ('FLOW_PRG/SEARCH.BIN', '@2c58c#0'),
        ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT1.TBD#2'), ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT2.TBD#0'),
        ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT3.TBD#0'), ('ETC_DATA/PL_EDIT.ZAR', 'PL_PT4.TBD#0')]
for iso, tid in mine:
    src = os.path.join(root, 'translation', 'textures', *iso.split('/'), tid + '.pvr')
    dst = os.path.join(root, 'build', 'art3_tex', *iso.split('/'), tid + '.pvr')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    print(dst)
