"""Read-only: energy profile of the CDDA tracks 2 and 4 (16-bit stereo, 2352 B sectors). usage: dxp_audio.py"""
import numpy as np, os
B = 'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan) (Track %d).bin'
for t in (2, 4):
    d = np.fromfile(B % t, dtype='<i2')
    n = len(d) // (2352 // 2)
    d = d[:n * 1176].reshape(n, 1176).astype(np.float64)
    rms = np.sqrt((d ** 2).mean(axis=1))
    nz = int((rms > 0).sum())
    print('track', t, 'sectors', n, 'nonzero sectors', nz, 'rms>100:', int((rms > 100).sum()), 'max rms %.0f' % rms.max())
    # first/last nonzero
    idx = np.nonzero(rms > 0)[0]
    if len(idx): print('  first/last nonzero sector', idx[0], idx[-1])
    seg = 450 if t == 4 else 50
    print('  rms per %d sectors:' % seg, [int(rms[i:i + seg].mean()) for i in range(0, n, seg)][:30])
