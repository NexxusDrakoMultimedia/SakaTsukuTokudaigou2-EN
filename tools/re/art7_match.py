"""art7_match: find the same label sprite (alpha mask) in other textures, so one translated label repaints every copy.
find(arr, ref_mask, thr) -> [(x, y, iou)] best first, non-overlapping."""
import numpy as np


def _mask(arr, a=128):
    return arr[..., 3] >= a


def tight(arr, rect, a=100):
    """Tight ink bbox (x,y,w,h) of the alpha mask inside the rough rect."""
    x, y, w, h = rect
    m = arr[y:y + h, x:x + w, 3] >= a
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        raise ValueError('no ink in %r' % (rect,))
    return (x + int(xs.min()), y + int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


def _fast(n):
    k = 1
    while k < n:
        k *= 2
    return k


class Target:
    """Caches the target's mask, integral image and FFT."""

    def __init__(self, arr):
        self.T = _mask(arr)
        self.H, self.W = self.T.shape
        self.P = (_fast(self.H * 2), _fast(self.W * 2))
        self.Ft = np.fft.rfft2(self.T.astype(np.float32), self.P)
        self.ii = np.pad(self.T.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))


def find(arr, ref, thr=0.85, maxn=12):
    """ref: bool mask (h, w).  arr: RGBA target or a Target."""
    tg = arr if isinstance(arr, Target) else Target(arr)
    T, H, W, P, Ft = tg.T, tg.H, tg.W, tg.P, tg.Ft
    h, w = ref.shape
    if h > H or w > W:
        return []
    Fr = np.fft.rfft2(ref[::-1, ::-1].astype(np.float32), P)
    cc = np.fft.irfft2(Ft * Fr, P)
    # inter at window top-left (x,y) = cc[y+h-1, x+w-1]
    inter = cc[h - 1:H, w - 1:W]
    ii = tg.ii
    win = ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]
    win = win[:H - h + 1, :W - w + 1]
    r = float(ref.sum())
    iou = inter / np.maximum(r + win - inter, 1.0)
    out = []
    iou = iou.copy()
    for _ in range(maxn):
        k = int(np.argmax(iou))
        y, x = divmod(k, iou.shape[1])
        v = float(iou[y, x])
        if v < thr:
            break
        out.append((x, y, v))
        iou[max(0, y - h + 1):y + h, max(0, x - w + 1):x + w] = 0
    return out
