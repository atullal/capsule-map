---
name: vinyl-animation
description: Create, adapt, and validate artwork-aware light animations for vinyl sleeves using Capsule Map. Use for one album worker, ink masks, beat choreography, and reusable animation modules before projector composition.
---

Create light that follows the printed features of one album. The coordinator provides a verified reference, timing, isolated output directory, and any calibration. Read [the worker contract](references/worker-contract.md) before writing code. This workflow is plain files plus Python/OpenCV and works with any agent that can inspect images and execute those tools.

## Work in the assigned scope

Locate the Capsule Map checkout from the assignment; do not assume the installed skill directory is the repository. Use `build/mapping-venv/bin/python` when that environment exists. The existing source animation helpers live in the supplied projection-mapping checkout; treat it read-only. Existing examples are `tools/triptych/crimson.py` and the source project's `animate_hox.py`, `animate_hox_show.py`, and `animkit.py`.

Inspect only the assigned reference, needed code, and optional calibration artifacts. Do not load entire photo sweeps into an animation worker. Keep writes inside its output directory. The coordinator owns ADB, camera captures, calibration files, shared manifests, composition, and deployment.

## Author and check

- Identify named printed features and make a regions overlay before animating. Derive masks from the actual edition: eyes, lettering, circuits, petals, instruments, or other recognisable details. Keep coordinates in 1400×1400 artwork space.
- Preserve the drawing. Animate illumination along its lines, color layers, and focal features. Sample the print's own colors; use light ink for hue changes. Dark ink has low reflectance and should not receive a bright generic rectangle. Favor traveling highlights along contours over unrelated flat wipes.
- Precompute masks, distance fields, and coordinate grids once in `setup`; `frame_light(t)` should only combine cached arrays. Cache expensive geodesics in the worker directory. Never import pygame into an OpenCV process.
- Use the coordinator's shared beat grid and computed frames per beat. Whole-cycle periodic phases plus a dark entrance and exit create a loop without a seam. Preview both endpoints and representative beats/scenes.
- Return finite float BGR frames in [0,1]. Apply artwork-space sleeve/beam alpha when supplied. Author in artwork space and let the coordinator warp once into projector space; do not bake a second homography into the animation.
- Inspect the regions overlay and contact sheet, correct feature masks or poor visual balance, and validate sampled frames. Return concrete artifacts and a short report. A contact sheet validates animation design, not physical alignment; only an inspected projected edge/photo can establish that.

For the existing three-cover implementation, `tools/triptych/render.py --help` exposes the reference renderer. It still knows those three album layouts. New albums need their own module and calibration, not renamed existing masks.
