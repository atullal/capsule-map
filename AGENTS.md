# Working on Capsule Map

Read [README.md](README.md) for scope and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for data flow. Use [docs/SETUP.md](docs/SETUP.md) for a fresh checkout. Run commands from the repository root. Do not assume the author's device address, home directory, private build artifacts, or existing calibration is available.

## Code ownership

- `src/dev/atul/capsulemap/`: Android app, local server, projection, playback and capture overlay.
- `web/controller.html`: controller source. `tools/embed_controller.py` regenerates its Java embedding during build; do not maintain two independent HTML copies.
- `tools/camera/`: bridge APK and single/batch camera capture.
- `tools/album/`, `tools/triptych/`: registration, animation and deployment wrappers.
- `vendor/projection-mapping/`: MIT-licensed helper snapshot. Prefer wrapper changes; if editing vendored code, preserve its license and update the snapshot notes/hashes to describe the modification.
- `skills/`: reusable agent workflows. Keep their commands consistent with actual CLI flags.

## Essential invariants

1. One coordinator owns all projector/camera operations. Do not run device tests, single photos, or media changes during another capture. Acquire ownership explicitly before using a shared device and release it when finished. Never delete an active device lock.
2. Keep OpenCV and pygame in separate processes. Host tools here use OpenCV; native Android handles projection.
3. Camera photos are 1280×720, projector output is 1920×1080, and artwork frames are 1400×1400 float BGR in [0,1]. Raw factory JPEGs are upside-down; rotate once on import. Name mapping directions explicitly.
4. Author illumination in artwork space and apply the calibrated projector warp once. Prewarped video must not receive the manual quad transform again. Preserve black gaps between objects.
5. Calibration needs a fresh isolated capture. Movement of objects, projector, focus or keystone invalidates physical alignment. Never relabel failed/partial captures as complete or bypass checksum and fit gates to obtain output.
6. A low fitting RMS is not optical proof. Inspect an actual projected outline photograph before recording verification. Do not invent inspection notes or copy another setup's verification evidence.
7. Keep animation timing on a shared beat grid and inspect dark loop endpoints. The existing multi-album renderer uses 100 BPM, 48 beats, 30 fps, 864 frames; changing timing requires coordinated worker/composition changes.
8. The factory camera is a vendor workaround, not a public Camera2 API or continuous stream. Preserve the opaque capture overlay, atomic capture exclusion, cleanup and watchdog. Temporary busy errors must not yield accepted stale photos.
9. Do not commit room photos, downloaded album artwork, rig-specific maps, generated video/APKs, credentials or signing keys. Use ignored `build/` for artifacts. Never force-add these as a shortcut to a working demo.

## Working with agents

Use [vinyl-show-parallel](skills/vinyl-show-parallel/SKILL.md) when parallel album work is requested and the runtime permits delegation. Give each worker a separate output directory, exact timing and immutable inputs. Workers may research, author masks and render offline; the coordinator alone changes device state and shared calibration. A process pool is not an AI model delegation tool. Do not claim a provider/model was tested unless it actually ran.

## Validation matched to the change

- Docs/config: check links, CLI flags and `git diff --check`; do not interrupt the projector.
- Capture import: `build/mapping-venv/bin/python tools/camera/test_batch.py`.
- Python: `build/mapping-venv/bin/python -m compileall -q tools vendor/projection-mapping` and relevant CLI help/import checks.
- Android/controller: build both APKs as documented; perform relevant device checks only when device ownership is available and the task authorizes hardware work.
- Geometry: fresh capture, numerical checks, projected outline and inspected sensor photo.
- Animation: inspect masks/contact sheets and sampled frame bounds; for a changed production show, render, deploy and inspect playback when hardware is available. Reduced previews cannot certify all frames or physical alignment.
- Camera changes: test bounded smoke capture and restoration; full structured-light changes need a complete sweep and decoding check.

Build/test requirements and hardware limitations belong in the final report. Distinguish checks actually run from those requiring unavailable hardware or local assets. Do not broaden tests or rerender unchanged shows after the relevant checks pass.

## Publication

Follow the user's branch/commit/push request. Avoid rewriting shared history. Preserve unrelated work. Before publishing, review tracked files and confirm generated/private artifacts remain ignored. A clean source checkout should build without the original laptop's paths; keep README/setup instructions current when defaults change.
