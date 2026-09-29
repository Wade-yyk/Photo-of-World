"""Optional extensions; the original intensity-NCC pipeline stays unchanged."""
import numpy as np
from PIL import Image, ImageFilter
from alignment import downsample, search


def edges(channel):
    """Smoothed gradient magnitude, robustly scaled; features used only for search."""
    image = Image.fromarray(np.round(channel * 255).clip(0, 255).astype('uint8'))
    smooth = np.asarray(image.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255
    gy, gx = np.gradient(smooth)
    magnitude = np.hypot(gx, gy)
    scale = max(float(np.percentile(magnitude, 99)), 1e-6)
    return np.minimum(magnitude / scale, 1).astype(np.float32)


def gradient_align(reference, moving):
    refs, movs = [reference], [moving]
    while max(refs[-1].shape) > 192:
        refs.append(downsample(refs[-1]))
        movs.append(downsample(movs[-1]))
    offset, trace = (0, 0), []
    for level in range(len(refs) - 1, -1, -1):
        radius = 15 if level == len(refs) - 1 else 2
        if level < len(refs) - 1:
            offset = (offset[0] * 2, offset[1] * 2)
        offset, score = search(edges(refs[level]), edges(movs[level]), radius, offset)
        trace.append({'level': level, 'offset': list(offset), 'ncc': float(score)})
    return offset, trace


def detect_crop(image):
    """Detect straight scan borders using row/column profiles, not a preset crop.

    Look for strong cross-channel transitions near each outside edge, supported
    by black/white/colour-inconsistent boundary pixels. The 15% search limit is
    only a guard against cutting deep into the photograph; no detection => 0.
    """
    small = image.convert('RGB').copy()
    small.thumbnail((900, 900), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float32) / 255

    def side_cut(strip):
        # Each row runs parallel to the candidate side; suppress corner borders.
        length, across = strip.shape[:2]
        strip = strip[:, int(across * .15):max(int(across * .85), 1)]
        limit = max(2, int(length * .15))
        median = np.median(strip, axis=1)
        channel_range = np.ptp(strip, axis=2)
        extreme = ((strip.min(axis=2) < .075) | (strip.max(axis=2) > .97))
        colour = (channel_range > .32) & ((strip.min(axis=2) < .22) | (strip.max(axis=2) > .8))
        bad = np.mean(extreme | colour, axis=1)
        # A scan edge tends to move many pixels in the same direction at once.
        delta = np.abs(np.diff(median, axis=0)).max(axis=1)
        floor = np.median(delta[limit:]) if len(delta) > limit else 0
        threshold = max(.035, float(floor) * 4)
        candidates = []
        for i in range(1, min(limit, len(delta) - 3)):
            previous_bad = float(np.mean(bad[max(0, i-4):i+1]))
            following_bad = float(np.mean(bad[i+1:i+5]))
            change = float(delta[i])
            if change > threshold and previous_bad > .32 and following_bad < previous_bad - .10:
                candidates.append(i + 1)
        if candidates:
            return min(candidates[-1] + 1, limit)
        # Uniform black/white strips can have a soft transition rather than a peak.
        if bad[0] > .8:
            for i in range(1, limit):
                if np.all(bad[i:i+4] < .3):
                    return i
        return 0

    left = side_cut(arr.transpose(1, 0, 2))
    right = side_cut(arr[:, ::-1].transpose(1, 0, 2))
    top = side_cut(arr)
    bottom = side_cut(arr[::-1])
    sx, sy = image.width / small.width, image.height / small.height
    bounds = (round(left*sx), round(top*sy), image.width-round(right*sx), image.height-round(bottom*sy))
    return bounds


def white_balance(array, stats_bounds):
    x0, y0, x1, y1 = stats_bounds
    sample = array[y0:y1, x0:x1]
    pixels = sample.reshape(-1, 3)
    usable = pixels[(pixels.min(axis=1) > .02) & (pixels.max(axis=1) < .98)]
    if len(usable) < 32:
        usable = pixels
    means = usable.mean(axis=0, dtype=np.float64)
    gains = np.clip(means.mean() / np.maximum(means, 1e-6), .65, 1.55)
    # Protect highlights by a single common exposure factor, retaining gain ratios.
    balanced = array * gains
    sample = balanced[y0:y1, x0:x1]
    exposure = max(1., float(np.percentile(sample, 99.5)))
    balanced /= exposure
    return np.clip(balanced, 0, 1), (gains / exposure).tolist()


def contrast(array, stats_bounds):
    x0, y0, x1, y1 = stats_bounds
    lo, hi = np.percentile(array[y0:y1, x0:x1], (1, 99))
    if hi - lo < 1e-6:
        return array.copy(), [float(lo), float(hi)]
    return np.clip((array-lo)/(hi-lo), 0, 1), [float(lo), float(hi)]


def apply_tone(image, stats_bounds, balance=False, stretch=False):
    array = np.asarray(image.convert('RGB'), dtype=np.float32) / 255
    gains, levels = [1., 1., 1.], [0., 1.]
    if balance:
        array, gains = white_balance(array, stats_bounds)
    if stretch:
        array, levels = contrast(array, stats_bounds)
    return Image.fromarray(np.round(array*255).astype('uint8')), {'gains': gains, 'levels': levels}


def colour_mapping(image):
    """Experimental fixed 3x3 mapping: retain 85% of chroma around luma.

    This is a transparent aesthetic mapping in encoded RGB, not a calibrated
    recovery of historical filter responses. No ground-truth colours are known.
    """
    weights = np.array([.2126, .7152, .0722])
    matrix = .85*np.eye(3) + .15*np.tile(weights, (3, 1))
    pixels = np.asarray(image, dtype=np.float32) / 255
    mapped = pixels @ matrix.T
    return Image.fromarray(np.round(np.clip(mapped, 0, 1)*255).astype('uint8')), matrix.tolist()
