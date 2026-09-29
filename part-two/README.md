# Part Two: Images of the Russian Empire

First implementation: zero-mean NCC with integer translations, one fixed parameter set for all 22 supplied images. Original files stay in the sibling `data/` directory and are never modified.

## Reproduce

From the repository root, with Python 3.10+:

```sh
python -m pip install -r scripts/alignment-requirements.txt
python scripts/test_alignment.py
python scripts/run_alignment.py --input ../data --output part-two/results
python scripts/run_enhancements.py --input ../data --results part-two/results
python scripts/add_colour_variants.py
python scripts/build_part_two.py
python -m http.server 8000
```

Open `http://localhost:8000/part-two/`. The generated page also works directly from `index.html`; its metrics are embedded, so no fetch/server is required.

## Algorithm

1. Convert the provided scan to floating-point grayscale [0, 1], divide height into three equal floor(H/3) sections in B, G, R order, discard only the final H % 3 rows.
2. Keep B fixed; search G and R independently. Positive (dx, dy) shifts the moving image right/down.
3. Score zero-mean NCC on overlapping interiors, excluding 10% of each edge from both channels. Different displacement candidates may use slightly different valid overlap sizes. No wraparound pixels contribute.
4. Reduced single-scale baseline: large channels are capped at 400 px for a quick comparison, while smaller plates stay at native resolution; exhaustive ±15 px search. The 400 px cap is an implementation choice, not an assignment requirement.
5. Pyramid: manually smooth with Gaussian sigma=1 and subsample by 2 until the longest side <=192 px. Search ±15 on the smallest layer, double shifts, refine ±2 on each finer layer, including full resolution. No library registration or pyramid routines. Coarse Gaussian layers are represented at 8-bit precision; full-resolution scoring uses original float channels. NCC reductions accumulate in float64.
6. Stack aligned R, G, B on their common valid rectangle. This removes out-of-bounds areas, not all scan borders. Compare-before images use exactly the same B-coordinate rectangle as compare-after images.

## Outputs

- `results/offsets.csv`: 36 rows, two methods per input, with per-method dimensions, offsets and timings.
- `results/results.json`: full metrics, crop bounds, and each pyramid level's trace.
- Per input: source preview, B/G/R previews, unaligned view, low-resolution baseline, aligned web preview, and original-resolution aligned JPEG.
- `aligned-full.jpg` preserves original pixel resolution within the common crop; previews have maximum side 1100 px.
- Timings include alignment searches for both G and R (and pyramid creation for that method), but exclude reading/writing files. Single-scale and pyramid timings use different input resolutions on large scans and are not a controlled speed benchmark.

## Current scope and limitations

All 22 local images are processed, including 6 scans around 3700 × 9700 px and the four added `service-pnp-prok-*_150px.jpg` plates. The original baseline files and metrics are preserved. Optional features are described below. Damage in 00056v and some scan borders/colour fringes remain visible. Neither method claims perfect alignment on every plate.

The generated HTML comes from `scripts/build_part_two.py`; edit that generator before rebuilding. Styles and browser interactions live in `part-two.css` and `part-two.js`.

## Optional features (all off by default)

Generate these after the baseline batch and before rebuilding the HTML:

```sh
python scripts/test_enhancements.py
python scripts/run_enhancements.py --input ../data --results part-two/results
python scripts/add_colour_variants.py
python scripts/build_part_two.py
```

The page builder now requires `results/features.json`. These scripts generate 32 combinations for each photograph, stored only under its new `features/` directory. `run_enhancements.py` verifies SHA-256 hashes of all baseline assets before and after execution; it does not replace those assets.

Each photograph has independent checkboxes, synchronized with the large comparison viewer. Switching the gallery to Before or Single-scale suspends optional features and remembers the selections. Reset restores the exact original `aligned.jpg` asset. Selections persist during the current page session, not across reloads.

1. **Gradient alignment:** recompute the manual full-resolution pyramid using NCC on smoothed gradient magnitude at each level; map the resulting shifts back to the original channels. Offsets and runtime are logged. No per-image parameter tuning.
2. **Automatic crop:** use row/column median transitions with brightness and colour border evidence. Inspect at most 15% from each edge as a safety limit, rather than applying a fixed 15% crop. An undetected edge is left unchanged. Profiles are computed on an image no larger than 900 px and mapped to source coordinates. Per-photo yellow-box diagnostics and actual crop bounds are available. This heuristic can miss faint borders or mistake a strong scene boundary for a scan boundary.
3. **Gray-world white balance:** compute RGB means within the detected interior, excluding extreme pixels; gains are clamped to 0.65–1.55 before a common highlight-protection exposure factor. Dominant-colour scenes can become less natural. This is optional, not a guarantee of more accurate colours.
4. **Automatic contrast:** use a shared 1st–99th percentile mapping across RGB, estimated on the detected interior after white balance when enabled. Clipping can discard extreme highlight/shadow details.
5. **Experimental colour mapping:** a fixed matrix M = 0.85 I + 0.15 [1,1,1]^T [0.2126,0.7152,0.0722], applied last in encoded RGB. It retains 85% of chroma and preserves neutral pixels. It is a reproducible aesthetic experiment, **not** a calibrated estimate of historical filter responses or verified true colours.

Alignment is performed at original resolution. Optional tone variants are web previews (maximum side 1100 px); links label this explicitly. Original full-resolution NCC results remain downloadable in Processing details. Gradient-only full-resolution results are also saved as `features/gradient-full.jpg`.

Comparison fairness: with all options off, the viewer compares original unaligned/aligned assets. With any option on, it compares baseline NCC with the selected effects on the exact same source-coordinate rectangle. Gradient results first use the common valid region of both alignments; auto-crop, if selected, then applies identically to both comparison sides. Tone statistics always exclude detected borders, even if crop display is off.

`features.json` records gradient offsets and traces, detected rectangles, preview sizes, white-balance gains, contrast ranges, and colour matrices. Variant filenames use a bit mask: gradient=1, crop=2, white balance=4, contrast=8, colour mapping=16.
