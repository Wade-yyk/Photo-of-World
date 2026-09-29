"""Translation-only BGR plate alignment using zero-mean NCC and a manual pyramid.

Offsets are (dx, dy) to apply to the moving channel; positive = right/down.
No roll/wraparound and no automatic-registration or pyramid library calls.
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageFilter


def split_plate(image):
    gray = np.asarray(image.convert('L'), dtype=np.float32) / 255.0
    height = gray.shape[0] // 3
    if height < 3:
        raise ValueError('Plate is too short to split into B, G and R.')
    return tuple(gray[i * height:(i + 1) * height].copy() for i in range(3))


def ncc_score(reference, moving, dx, dy, border=0.10):
    """Compare only the overlapping interiors; exclude scan borders on BOTH images."""
    h, w = reference.shape
    my, mx = max(1, int(h * border)), max(1, int(w * border))
    y0, y1 = max(my, my + dy), min(h - my, h - my + dy)
    x0, x1 = max(mx, mx + dx), min(w - mx, w - mx + dx)
    if y1 - y0 < 8 or x1 - x0 < 8:
        return -float('inf')
    a = reference[y0:y1, x0:x1]
    b = moving[y0-dy:y1-dy, x0-dx:x1-dx]
    count = a.size
    sa, sb = a.sum(dtype=np.float64), b.sum(dtype=np.float64)
    aa = np.einsum('ij,ij->', a, a, dtype=np.float64, optimize=False) - sa * sa / count
    bb = np.einsum('ij,ij->', b, b, dtype=np.float64, optimize=False) - sb * sb / count
    ab = np.einsum('ij,ij->', a, b, dtype=np.float64, optimize=False) - sa * sb / count
    denominator = np.sqrt(max(aa, 0) * max(bb, 0))
    return float(ab / denominator) if denominator > 1e-12 else -float('inf')


def search(reference, moving, radius=15, initial=(0, 0), border=0.10):
    best, best_score = tuple(initial), -float('inf')
    for dy in range(initial[1] - radius, initial[1] + radius + 1):
        for dx in range(initial[0] - radius, initial[0] + radius + 1):
            score = ncc_score(reference, moving, dx, dy, border)
            if score > best_score or (score == best_score and dx*dx+dy*dy < best[0]**2+best[1]**2):
                best, best_score = (dx, dy), score
    if not np.isfinite(best_score):
        raise ValueError('No usable NCC match (too small or zero-variance image).')
    return best, best_score


def downsample(image):
    # Gaussian anti-aliasing, then explicit factor-two subsampling.
    # Quantization is limited to the smoothed coarse layers, not the original.
    smooth = Image.fromarray(np.round(image * 255).clip(0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    return np.asarray(smooth, dtype=np.float32)[::2, ::2].copy() / 255.0


def pyramid_align(reference, moving, coarse_size=192, coarse_radius=15, refine_radius=2, border=0.10):
    refs, movs = [reference], [moving]
    while max(refs[-1].shape) > coarse_size:
        refs.append(downsample(refs[-1])); movs.append(downsample(movs[-1]))
    offset, trace = (0, 0), []
    for level in range(len(refs)-1, -1, -1):
        coarsest = level == len(refs)-1
        if not coarsest:
            offset = (offset[0]*2, offset[1]*2)
        predicted = offset
        radius = coarse_radius if coarsest else refine_radius
        offset, score = search(refs[level], movs[level], radius, predicted, border)
        trace.append({'level':level, 'scale':2**level, 'width':refs[level].shape[1], 'height':refs[level].shape[0], 'prediction':list(predicted), 'offset':list(offset), 'radius':radius, 'ncc':round(score,6)})
    return offset, trace


def low_resolution(channels, max_side=400):
    h,w=channels[0].shape
    scale=min(1.0,max_side/max(h,w))
    size=(max(1,round(w*scale)),max(1,round(h*scale)))
    result=[]
    for channel in channels:
        image=Image.fromarray(channel,mode='F')
        result.append(np.asarray(image.resize(size,Image.Resampling.LANCZOS),dtype=np.float32))
    return tuple(result)


def compose(channels, green=(0,0), red=(0,0), bounds=None):
    """RGB on the common valid canvas; no synthetic wrapped pixels."""
    h,w=channels[0].shape
    offsets=[(0,0),green,red]
    if bounds is None:
        x0=max(d[0] for d in offsets); x1=min(w+d[0] for d in offsets)
        y0=max(d[1] for d in offsets); y1=min(h+d[1] for d in offsets)
        bounds=(x0,y0,x1,y1)
    x0,y0,x1,y1=bounds
    if x1<=x0 or y1<=y0:
        raise ValueError('Aligned channels have no common overlap.')
    aligned=[ch[y0-dy:y1-dy,x0-dx:x1-dx] for ch,(dx,dy) in zip(channels,offsets)]
    rgb=np.stack(aligned[::-1],axis=-1)
    return Image.fromarray(np.round(rgb*255).clip(0,255).astype(np.uint8)),bounds
