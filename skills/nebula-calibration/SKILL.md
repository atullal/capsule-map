---
name: nebula-calibration
description: Capture a structured-light calibration batch locally on the Nebula Capsule projector, download verified camera photos, fit surface maps, and inspect projected alignment.
---

Use the Capsule Map repository, currently `/Users/atullal/Documents/ChatGPT/capsule-mapping`. Resolve its actual location before running commands. Python is `build/mapping-venv/bin/python`; the installed app, camera bridge, authorized ADB and overlay permission are prerequisites. Read `tools/camera/README.md` only for setup or troubleshooting.

One coordinator owns the projector throughout capture and verification. Animation agents can work offline concurrently, but must not change projector output. Keep projector, sleeves, focus and keystone fixed for the entire calibration. A moved setup requires a fresh run; old calibration files cannot certify current alignment.

## Collect once on the projector

Find the authorized serial with `adb devices -l`. Run from the repo:

```sh
build/mapping-venv/bin/python tools/camera/batch.py --serial SERIAL --run build/NEW-CAPTURE --resume-media three-vinyls.mp4
```

The projector generates 38 STEP4 Gray patterns locally, holds them above the factory camera UI, and saves JPEGs/checksums/timings locally. Only after acquisition does the client fetch one tar bundle, validate it, rotate photos180 degrees, and create `session.json`, `shots/`, `contact-sheet.jpg` and `ai-input.json`. No model calls or laptop per-photo commands occur inside the sequence. Acquisition is still bounded by the vendor camera delay. `--limit 2` is a smoke test and produces a partial session that cannot calibrate.

Read `ai-input.json` and inspect `shots/white.png`, `shots/black.png`, and the contact sheet. This is the AI handoff; the script does not upload private images to an unspecified cloud provider. In an agent session, load the images through available image-view tools. Check that patterns illuminate the intended objects, contrast exists, and no factory preview contaminated the photos.

On timeout, inspect `receipt.json` and the retained remote status/error/log before retrying. Do not mix sessions or force a failed/partial status to complete. The device restores playback; if it failed, inspect the local status and restore the selected staged media. Never delete an active capture lock.

## Fit and physically verify

For the existing three-sleeve arrangement:

```sh
build/mapping-venv/bin/python tools/triptych/calibrate.py --capture build/NEW-CAPTURE --output build/NEW-SHOW --references build/three-vinyls/reference
```

Its camera ROIs describe the original three-sleeve setup; inspect and update them for moved or different objects. For one sleeve use `tools/album/register_dense.py --run build/NEW-CAPTURE --reference ABSOLUTE-ARTWORK` with optional camera-space `--roi`. These scripts use the supplied `/Users/atullal/Projects/projection-mapping` algorithms read-only.

Reject bad contrast, missing photos, changed checksums, insufficient feature support, non-finite maps or failed held-out fit gates. Numerical RMS is not proof of optical alignment. Project the resulting `edge-test.png`, take an upright photo with `tools/album/snapshot.py`, inspect printed-feature alignment and clipping, then record verification with the relevant renderer's contract. Read `tools/triptych/README.md` for the three-sleeve contract or `tools/album/README.md` for one sleeve. Do not fabricate a verification note to unblock a render.

After maps are verified, independent album animation agents may share read-only maps and write isolated outputs using `vinyl-show-parallel`. Camera acquisition remains serial because all objects share one projector and sensor.
