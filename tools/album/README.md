# Calibrated album playback on Nebula

This workflow uses the supplied `vendor/projection-mapping` project read-only. It reuses its relative-contrast Gray-code decoding, SIFT artwork registration, homography plus cubic residual fitting, ink-aware artwork animation, and single projector-space warp. OpenCV and pygame never share a process. Nebula's internal factory camera replaces the source project's webcam, and Android hardware video playback replaces HDMI/pygame.

## Fresh calibration

Keep the projector, artwork, focus, and keystone settings fixed throughout capture, verification, rendering, and playback. Each run must use a **new directory**; capture never resumes an old photo cache. It records all pattern hashes and completion status. A failed capture remains available for diagnosis but cannot become a calibration.

```sh
build/mapping-venv/bin/python tools/camera/batch.py --serial PROJECTOR_IP:ADB_PORT --run build/my-new-run
build/mapping-venv/bin/python tools/album/register_dense.py --run build/my-new-run --reference /absolute/path/to/album-front.jpg
```

The source path can be changed with `--source`. Registration accepts an optional `--roi '[[x,y],...]'` camera polygon when multiple similar surfaces confuse artwork matching. It no longer uses the old manual-corner prior or a hard-coded sleeve polygon. The algorithm initially fits a coarse homography, then re-admits points explained by the cubic model so bowed sleeve edges are retained.

Quality gates reject missing/corrupt captures, fewer than 60 artwork matches, fewer than 2,000 consistent surface points, artwork registration RMS above 6 artwork pixels, mapping RMS above 3 projector pixels, held-out RMS above 3.5 projector pixels, non-finite lookups, or less than 25% artwork coverage. The held-out set uses spatially interleaved camera blocks. These thresholds are prototype acceptance limits, not a promise of optical accuracy.

Output is prepared in a separate directory and promoted to `calib/` only after all gates pass. Existing calibrations are never overwritten. `--legacy-shots` is an explicit offline analysis escape hatch for captures without a manifest; it does not assert that an old capture matches today's setup.

## Verify physical alignment

```sh
adb -s PROJECTOR_IP:ADB_PORT push build/my-new-run/calib/edge-test.png /sdcard/Android/data/dev.atul.capsulemap/files/edge-test.png
adb -s PROJECTOR_IP:ADB_PORT shell am start -n dev.atul.capsulemap/.MediaActivity --es file edge-test.png
build/mapping-venv/bin/python tools/album/snapshot.py --serial PROJECTOR_IP:ADB_PORT --output build/my-new-run/edge-verification.png --resume edge-test.png
```

Inspect the photograph: projected white lines must track the printed features. The guarded JPEG capture excludes the factory preview and success label. After actually inspecting the photo, record the finding:

```sh
build/mapping-venv/bin/python tools/album/verify_calibration.py --run build/my-new-run --photo build/my-new-run/edge-verification.png --note 'Describe the observed alignment and any clipping.'
```

This command records an operator judgment and hashes the photograph and lookup; it does not judge alignment automatically. Physical movement after verification still requires a fresh calibration. The factory camera takes interrupting stills, not a simultaneous stream, so there is no continuous movement detection.

## Render and deploy Life & Love

The current animation renderer is specific to Skinshape's Life & Love artwork. Use that album reference for this renderer; other references require their own artwork-space animation. It produces a silent 16-second loop at 90 visual beats/minute, 24 fps, and 16 frames/beat.

```sh
build/mapping-venv/bin/python tools/album/render_demo.py --run build/my-new-run --sheet
build/mapping-venv/bin/python tools/album/render_demo.py --run build/my-new-run
build/mapping-venv/bin/python tools/album/deploy.py --run build/my-new-run --serial PROJECTOR_IP:ADB_PORT --name life-and-love-new.mp4
```

Full rendering requires a recorded verification photo that still matches its hash. Deployment checks the render/map association and frame sequence, encodes H.264, stages video plus a calibration report, verifies transfer SHA-256 checksums, then renames and starts playback. Keep distinct filenames to retain earlier demos. Photograph the live animation at different phases after deployment.

The phone controller lists local MP4s, plays/stops them, and reports playback and attached calibration metrics. Files are in `/sdcard/Android/data/dev.atul.capsulemap/files/`. Direct ADB playback remains available for calibration PNGs. `/state` now reports the active media player rather than only the hidden mesh/effect state.

Room photographs, source artwork, generated media and maps remain in ignored `build/`. Required MIT-licensed helper sources are bundled in `vendor/projection-mapping`; private reference art and captures are excluded.
