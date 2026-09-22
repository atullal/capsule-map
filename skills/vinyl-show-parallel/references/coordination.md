# Delegate and assemble

## Album-agent assignment

Use this task shape with actual paths and values:

> Use the vinyl-artwork and vinyl-animation skills at the supplied paths. Create the assigned album's animation for this show. Repository: `<repo>`; read-only helper source: `<source>`; album: `<artist / title / album_id>`; verified reference: `<path and SHA-256>`; read-only calibration: `<calib>`; timing: `<fps / bpm / beats / duration>`; visual direction: `<observed print features and request>`. Own only `<worker-output>`; put code, masks, region overlay, contact sheet, and worker-result.json there. Other agents are working on other albums. Do not use ADB, the camera, shared manifests, or calibration writes. Run the supplied preview command and inspect its images. Return artifact paths, validation evidence, and blockers.

For a research-only first stage, stop after `artwork.json` and the verified original. The coordinator may begin device calibration while reference research and artwork-space design proceed, but workers must wait for the final calibration snapshot before mapped renders.

## Current three-album renderer

Run from the repository root using its CV environment. The built-in adapters support `life`, `hox`, and `crimson`; new album IDs can use `--module` when their calibration and metrics are supplied. The renderer fixes timing at 100 BPM / 48 beats / 30 fps / 28.8 seconds; a different beat grid needs a compatible renderer change before assigning workers. Check its current `--help` for supported flags before execution. A custom module supplies illumination, not geometry: register the new surface and include its calibration metrics before mapped rendering.

```sh
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album life --preview-frames 6 --width 384
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album hox --preview-frames 6 --width 384
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album crimson --preview-frames 6 --width 384
```

Those independent preview commands can run concurrently. Their reduced-size outputs are for iteration and cannot be deployed. Custom animation modules use `--module /absolute/path/animation.py`, with `setup(calib_dir)` and `frame_light(t)`; see the animation skill's worker contract.

Mapped previews also require intact calibration and physical verification hashes. Without those inputs, make artwork-space previews instead. The source helper checkout can be changed with `--source` on renderer commands.

For approved existing modules, run the full album renders concurrently with bounded process count, then assemble:

```sh
build/mapping-venv/bin/python tools/triptych/parallel.py all --run build/triptych-show --workers 3
build/mapping-venv/bin/python tools/triptych/parallel.py assemble --run build/triptych-show
```

For custom modules, dispatch one `worker --run RUN --album ALBUM --module PATH` command per album, then `assemble --run RUN`; assembly reads and validates the selected module paths from the manifests. `all` selects built-in modules only. Preview assembly takes the same `--preview-frames 6 --width 384` flags and writes a non-deployable preview.

Each full worker owns `RUN/workers/ALBUM/frames/`, `manifest.json`, and `contact-sheet.jpg`; previews are under `RUN/previews/ALBUM/`. These renderer manifests are generated evidence and are separate from the agent-authored `worker-result.json`. Fingerprints and checksummed resume permit an unchanged completed album to be reused. Never manually mark incomplete render output complete. Keep a delegated agent's hand-written code in a separate owned folder from renderer-managed outputs.

After assembly, deployment is the coordinator's command:

```sh
build/mapping-venv/bin/python tools/triptych/deploy.py --run build/triptych-show --serial PROJECTOR_IP:ADB_PORT
```

Use the actual verified run path and currently connected serial. Before deployment confirm full-resolution production output, complete frames, unchanged mapping and physical verification. The `all` command performs render work, not AI delegation. Agent creation is performed separately by the runtime's available delegation tool.
