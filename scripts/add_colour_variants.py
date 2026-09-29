"""Add explicit experimental colour-matrix variants after the other effects."""
from pathlib import Path
import json
from PIL import Image
from enhancements import colour_mapping

results = Path(__file__).resolve().parents[1] / 'part-two/results'
path = results / 'features.json'
report = json.loads(path.read_text(encoding='utf-8'))
report['bits']['colour_mapping'] = 16
if 'experimental colour matrix' not in report['order']:
    report['order'].append('experimental colour matrix')
for record in report['images']:
    folder = results / record['id']
    for mask in range(16):
        info = record['variants'][str(mask)]
        with Image.open(folder / info['file']) as image:
            mapped, matrix = colour_mapping(image.convert('RGB'))
        name = f'features/{mask+16:02d}.jpg'
        mapped.save(folder / name, quality=92, optimize=True)
        record['variants'][str(mask+16)] = {**info, 'file': name, 'colour_matrix': matrix}
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('32 combinations available for each of', len(report['images']), 'images.')
