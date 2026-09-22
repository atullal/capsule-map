# Three-vinyl show

A 28.8-second / 48-beat / 100 BPM silent light show at 30 fps, mapped independently to the three sleeves observed by the Nebula internal camera. The projector plays one prewarped 1920×1080 H.264 video locally.

- Left: Skinshape, **Life & Love** — reuses the supplied project's artwork-aware neon lettering, sunburst, instruments, medallion and sunset choreography, retimed to the shared beat grid.
- Middle: Black Market Brass, **Hox** — adapts four scenes from the supplied project's show: circuit ignition, radar, data rain, spotlights/shockwave finale. Ink-distance fields carry light along the green/violet printed traces.
- Right: King Crimson, **In the Court of the Crimson King** — new `crimson.py` animation, with separately masked eyes, iris coronas, teeth, cheeks and mouth, travelling facial contours and internal mouth ripples. The print remains stationary; light illuminates its features.

Source animation helpers are imported read-only from `/Users/atullal/Projects/projection-mapping`. No OpenCV process imports pygame. Frames are authored in 1400×1400 artwork coordinates and warped once, then combined with black gaps between sleeves. Each loop starts and ends dark.

## Artwork

`python3 tools/triptych/download_art.py` fetches the matched editions and records their hashes. Matching covers were downloaded from artist/album pages, and exact image URLs are stored in ignored `build/three-vinyls/reference/sources.json`:

- [Life & Love — Skinshape](https://skinshape.bandcamp.com/album/life-love)
- [Hox — Black Market Brass](https://blackmarketbrass.bandcamp.com/album/hox)
- [In the Court of the Crimson King — Apple Music](https://music.apple.com/us/album/in-the-court-of-the-crimson-king-expanded-edition/918534711)

Artwork and private room photos remain under ignored `build/`.

## Calibration

`calibrate.py` checks the completed session and every photograph's checksum, then decodes a single 38-pattern camera sweep. Each reference is matched separately using several image scales, distinct camera-feature counting, spatial support checks, and masked ECC refinement. New guarded JPEG sessions have no factory success overlay; legacy screenshot sessions still mask that region. Dense homography-plus-cubic models account for projection geometry; interleaved held-out camera blocks check prediction error. An inset around each sleeve protects against wall spill.

The three broad search ROIs in `calibrate.py` describe the current observed arrangement. They must be rediscovered for another arrangement. This is a verified three-object demo, not a general object-identification service. In particular the small sensor view limits absolute registration accuracy; numerical residuals alone do not prove alignment. Always project and inspect the outline photograph after recalibration.

```sh
build/mapping-venv/bin/python tools/album/capture_patterns.py PROJECTOR_IP:PORT --run build/new-triptych-capture --resume-media black.png
build/mapping-venv/bin/python tools/triptych/calibrate.py --capture build/new-triptych-capture --output build/new-triptych-show --references build/three-vinyls/reference
```

Project `edge-test.png` from the show directory, photograph using `tools/album/snapshot.py`, inspect it, and record `verification.json` with the photograph's SHA-256 plus the inspection note. The renderer requires that evidence to be present and unchanged.

```sh
build/mapping-venv/bin/python tools/triptych/render.py --run build/new-triptych-show --prepare
build/mapping-venv/bin/python tools/triptych/render.py --run build/new-triptych-show --sheet
build/mapping-venv/bin/python tools/triptych/render.py --run build/new-triptych-show --workers 4
build/mapping-venv/bin/python tools/triptych/deploy.py --run build/new-triptych-show --serial PROJECTOR_IP:PORT
```

Deployment checks frame completeness and calibration hashes, encodes and verifies duration, stages the video/report, verifies their device checksums, and starts `three-vinyls.mp4`. The existing phone controller can select it alongside earlier demos. Recalibrate and rerender after moving any sleeve, the projector, focus or keystone.

## Verified current run

`build/triptych-capture` contains the completed camera sweep; `build/triptych-show` contains the maps, contact sheet, edge check, live photos and deployed video. Unique feature matches: Life & Love 78, Hox 143, Crimson King 51. Held-out projector-space RMS: 2.08, 1.81 and 1.70 pixels respectively. Mask coverage is about 95% including the intentional edge inset; all three physical sleeves are inside the beam.

The outline projection and a rendered preview were inspected through the internal sensor, followed by two live-video photographs. Video duration is 28.800 seconds; all 864 frames were rendered; first and last frames are black. The deployed file's SHA-256 was checked on the device. Hardware playback was observed through 1,028 decoded frames (more than one loop) with zero dropped frames. The show is left running as `three-vinyls.mp4`.

## Independent agents and resumable rendering

`parallel.py` lets one agent own each album's module and render independently. The
coordinator alone captures, verifies calibration, assembles, and deploys. It runs
one isolated Python process per album and initializes only that album's masks;
OpenCV/native math threads are bounded to avoid oversubscribing the laptop.

```sh
# Fast draft across the whole timeline; never overwrites full-size deployed frames.
build/mapping-venv/bin/python tools/triptych/parallel.py all --run build/triptych-show --workers 3 --preview-frames 6 --width 384

# Production: execute these worker commands concurrently in separate agents.
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album life
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album hox
build/mapping-venv/bin/python tools/triptych/parallel.py worker --run build/triptych-show --album crimson
# Or dispatch all three subprocess workers with `all --workers 3`.
build/mapping-venv/bin/python tools/triptych/parallel.py assemble --run build/triptych-show
```

Workers write only `RUN/workers/ALBUM` (drafts use `RUN/previews/ALBUM`), including
lossless projector frames, `contact-sheet.jpg`, `manifest.json`, and private caches.
A source/calibration/settings fingerprint and each frame's checksum allow a repeat
run to reuse completed work; missing/corrupt frames are rebuilt. Input changes
invalidate the affected worker output. Same-album writers are excluded by a lock.
Assembly checks all workers, their calibration and frame checksums, combines layers
once, and writes the established `frames/` and `render.json` for `deploy.py`.
Draft assembly writes `RUN/preview/preview.json` instead and cannot be deployed by
the standard command. Both paths require existing inspected outline evidence;
new physical placement still requires a fresh capture and visual check.

Custom modules use `worker --album ID --module /absolute/path/animation.py` and
expose `setup(calib_dir)` plus `frame_light(t)`. Frames must be finite float BGR
1400×1400×3 arrays in [0,1], already masked in artwork space. The harness applies
the projector warp. Timing is currently fixed to the shared 28.8-second,
100 BPM, 30 fps show. Write caches beside the worker's module, never into read-only
calibration. Use `assemble --albums life,hox,crimson` after custom workers finish;
assembly reads their module locations from manifests. `--source` overrides the
helper checkout. The current `all` command dispatches built-in modules; coding
agents are orchestrated by the reusable [skills](../../skills/README.md).

`download_art.py --album ID` lets workers fetch one reference without overwriting
others. `--manifest SOURCES.json` accepts `{ "id": { "page": "https://...",
"artwork": "https://...jpg", "sha256": "optional expected digest" } }` for new
verified editions. Downloads and source registry updates are atomic; unchanged
verified artwork is reused. Actual edition matching remains the agent's visual task.
