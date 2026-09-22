# One album worker contract

The assignment contains:

- `repo`: Capsule Map checkout, and `source`: optional read-only projection-mapping helper checkout.
- `album_id`, artist/title, verified `reference` and source/checksum metadata.
- `output`: one exclusively owned worker directory; no sibling or shared writes.
- Timing: `fps`, `bpm`, `beats`, `duration_seconds`. Require duration = beats × 60 / bpm and an integral number of frames; derive frames per beat.
- Optional read-only `calib` with `reference.png`, `sleeve.png`, `covered.png`, and `render_map.npz`. Missing calibration does not prevent artwork-space design previews.
- Requested visual direction and available helpers, plus a command for the coordinator's compatible preview harness. The current parallel renderer supports the three existing album IDs and requires calibration; for a new album or no calibration, create artwork-space previews first and return the module for coordinator integration.

For `tools/triptych/parallel.py`, a custom module exposes `setup(calib_dir)` and `frame_light(t)`. `calib_dir` is a pathlib.Path containing the verified reference and masks. An adapter can load `reference.png` and compute sleeve/beam alpha, then call the two-argument `setup(reference, alpha)` illustrated by `tools/triptych/crimson.py`. Alpha is a 1400×1400 float [0,1] array. The frame result is a 1400×1400×3 finite float BGR array in [0,1]. Module-level timing constants must match the assignment. Import should not download files, access the projector, parse the coordinator's arguments, or launch rendering. If reusing a legacy module with another interface, use an explicit adapter and document it.

Return these worker-owned files:

- Animation module and any masks/cache needed by it.
- `regions.png`, labeling the real features used by the effects.
- `contact-sheet.jpg`, including t=0, the last frame, and representative scenes.
- `worker-result.json`: `album_id`, `status` (`complete` or `blocked`), `reference_sha256`, timing, animation/artifact paths, sample validation results, and outstanding limitations. Do not mark complete if imports, frames, or visual inspection failed.

Check at least both endpoint frames and one active frame: dimensions, finite values, range, dark endpoints, and nonzero content while active. Inspect the images, because numerical checks cannot establish that an eye mask covers an eye. Random effects should have a fixed seed and loop-safe time dependence so rendering out of order remains deterministic.

The coordinator chooses the final module location and composition adapter after review. Never alter geometry to hide animation mask errors. Never claim a current mapping is valid merely because its residuals are low; changes in sleeve, projector, focus, or keystone need fresh physical verification.
