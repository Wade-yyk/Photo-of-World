"""Create browser-ready JPEGs and the near-to-far-to-near dolly GIF.
Run: python -m pip install -r scripts/requirements.txt
     python scripts/prepare_media.py
Original images are never modified.
"""
from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets'
OUTPUT.mkdir(exist_ok=True)

for source in sorted((ROOT / 'images').iterdir()):
    if source.suffix.lower() not in {'.heic', '.jpg', '.jpeg'}:
        continue
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        image.save(OUTPUT / (source.stem.lower() + '.jpg'), quality=88, optimize=True)

frames = []
for number in range(8595, 8606):
    with Image.open(OUTPUT / f'img_{number}.jpg') as image:
        frames.append(ImageOps.pad(image.convert('RGB'), (480, 640), color='#161616'))
sequence = frames + frames[-2:0:-1]
sequence[0].save(
    OUTPUT / 'dolly-zoom.gif', save_all=True, append_images=sequence[1:],
    duration=[650 if i in (0, 10) else 160 for i in range(len(sequence))],
    loop=0, optimize=True,
)
print('Created web JPEGs and dolly-zoom.gif in', OUTPUT)
