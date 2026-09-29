"""Generate 16 reversible feature combinations without touching baseline files.

Mask bits: 1 gradient NCC, 2 detected crop, 4 gray-world WB, 8 contrast.
Gradient alignment runs at source resolution. Crop detection uses <=900 px
profiles. Tone processing and optional variants are web previews, <=1100 px.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
from PIL import Image, ImageDraw
from alignment import split_plate, compose
from enhancements import gradient_align, detect_crop, apply_tone


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(source, results):
    original_json = results / 'results.json'
    baseline = json.loads(original_json.read_text(encoding='utf-8'))
    protected = [p for p in results.rglob('*') if p.is_file() and 'features' not in p.parts and p.name != 'features.json']
    hashes = {str(p): digest(p) for p in protected}
    report = {'order': ['gradient alignment', 'detected crop', 'gray-world white balance', 'global contrast'],
              'preview_max_side': 1100, 'bits': {'gradient': 1, 'crop': 2, 'white_balance': 4, 'contrast': 8}, 'images': []}
    for row in baseline['images']:
        folder = results / row['id']
        out = folder / 'features'
        out.mkdir(exist_ok=True)
        with Image.open(source / row['source']) as plate:
            channels = split_plate(plate)
        start = time.perf_counter()
        green, gt = gradient_align(channels[0], channels[1])
        red, rt = gradient_align(channels[0], channels[2])
        seconds = time.perf_counter() - start
        edge_image, edge_bounds = compose(channels, green, red)
        edge_image.save(out / 'gradient-full.jpg', quality=94, optimize=True)
        with Image.open(folder / 'aligned-full.jpg') as original:
            original = original.convert('RGB')
        base_bounds = row['crop_bounds']
        common = (max(base_bounds[0], edge_bounds[0]), max(base_bounds[1], edge_bounds[1]),
                  min(base_bounds[2], edge_bounds[2]), min(base_bounds[3], edge_bounds[3]))
        entry = {'id': row['id'], 'gradient': {'green': list(green), 'red': list(red), 'seconds': round(seconds, 3),
                 'green_trace': gt, 'red_trace': rt, 'bounds': list(edge_bounds)}, 'variants': {}}
        for use_edges in (False, True):
            if use_edges:
                bounds = common
                image = edge_image.crop((common[0]-edge_bounds[0], common[1]-edge_bounds[1], common[2]-edge_bounds[0], common[3]-edge_bounds[1]))
                reference = original.crop((common[0]-base_bounds[0], common[1]-base_bounds[1], common[2]-base_bounds[0], common[3]-base_bounds[1]))
            else:
                bounds, image, reference = base_bounds, original.copy(), original.copy()
            detected = detect_crop(image)
            diagnostic = image.copy()
            diagnostic.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            scale_x, scale_y = diagnostic.width / image.width, diagnostic.height / image.height
            draw_box = [round(detected[0]*scale_x), round(detected[1]*scale_y), round(detected[2]*scale_x)-1, round(detected[3]*scale_y)-1]
            ImageDraw.Draw(diagnostic).rectangle(draw_box, outline='#ffce00', width=3)
            diagnostic.save(out / f'crop-detection-{int(use_edges)}.jpg', quality=92)
            for crop in (False, True):
                bit = int(use_edges) + 2*int(crop)
                current = image.crop(detected) if crop else image.copy()
                ref = reference.crop(detected) if crop else reference.copy()
                full_size = current.size
                current.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
                ref = ref.resize(current.size, Image.Resampling.LANCZOS)
                ref.save(out / f'reference-{bit}.jpg', quality=92, optimize=True)
                sx, sy = current.width / image.width, current.height / image.height
                stats = (0, 0, current.width, current.height) if crop else (
                    round(detected[0]*sx), round(detected[1]*sy), round(detected[2]*sx), round(detected[3]*sy))
                for balance in (False, True):
                    for stretch in (False, True):
                        mask = bit + 4*int(balance) + 8*int(stretch)
                        result, info = apply_tone(current, stats, balance, stretch)
                        result.save(out / f'{mask:02d}.jpg', quality=92, optimize=True)
                        entry['variants'][str(mask)] = {'file': f'features/{mask:02d}.jpg', 'reference': f'features/reference-{bit}.jpg',
                            'preview_size': list(result.size), 'source_area_size': list(full_size),
                            'detected_crop': list(detected), 'alignment_canvas': list(bounds), **info}
        report['images'].append(entry)
        print(f"{row['id']}: gradient G={green}, R={red}, {seconds:.2f}s; 16 options generated", flush=True)
    assert all(digest(Path(p)) == h for p, h in hashes.items()), 'A baseline file changed!'
    report['baseline_files_verified_unchanged'] = len(hashes)
    (results / 'features.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Baseline verified unchanged: {len(hashes)} files.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('../data'))
    parser.add_argument('--results', type=Path, default=Path('part-two/results'))
    args = parser.parse_args()
    run(args.input, args.results)
