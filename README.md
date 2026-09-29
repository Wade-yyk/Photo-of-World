# Photo of the World

Ke Yang · SYDE 671 · Assignment 1 · PART ONE

A static photography webpage inspired by the University of Waterloo's black, white, and gold visual style. No build step or JavaScript framework is required.

## View locally

Open `index.html` directly in a browser, or run `python -m http.server 8000` from this directory and visit http://localhost:8000.

## Included

- Portraits: five original selfies with distance and focal-length labels. Four have reversible abstract-image toggles; 0.8× remains an original-only portrait. The original 0.8× abstract image is mapped to 1.2×, and the 2.0× / 4.0× abstract images are swapped.
- Architecture: IMG_8609, IMG_8610, IMG_8613, and IMG_8615, labeled with their EXIF 35 mm equivalent focal lengths (206, 160, 97, and 24 mm).
- Dolly zoom: all 11 photographs, IMG_8595–IMG_8605, in near-to-far order; an animated reversing GIF; a draggable, keyboard-accessible frame slider; thumbnail selection; playback and step controls.
- English observations and explanations for all three experiments.
- Responsive layout, reduced-motion support, and print styles.
- `output/pdf/SYDE671-Part-One-Ke-Yang.pdf`: three-page static submission copy. The GIF is represented by still frames in print.

## Files

- `index.html`, `style.css`, `script.js`: webpage.
- `images/`: unchanged source photographs and supplied abstract images.
- `assets/`: browser-compatible JPEGs and `dolly-zoom.gif`.
- `scripts/prepare_media.py`: reproducible HEIC conversion and GIF generation.

To regenerate media, install `scripts/requirements.txt` in your Python environment, then run `python scripts/prepare_media.py`. The GIF uses the complete images without stabilization, preserving the handheld framing changes. It runs forward and backward with brief endpoint pauses.

Use the page's **Print / Save PDF** button to regenerate the PDF after editing. Enable background graphics in the browser print dialog. Print mode restores original portraits and displays the first and last dolly frames.

## Publishing

This folder is ready for static hosting, including GitHub Pages. Keep `index.html` at the publishing root with `style.css`, `script.js`, and `assets/` beside it. All project asset references are relative, so a repository subpath works. The site is published at https://wade-yyk.github.io/Photo-of-World/.

## Part Two

Open `part-two/index.html` for all 18 Prokudin-Gorskii reconstructions. The original NCC results are preserved. Each photo has independent optional controls for gradient alignment, detected border cropping, gray-world white balance, global contrast, and an experimental colour matrix. See `part-two/README.md` for the algorithms, limitations, and reproducible commands.
