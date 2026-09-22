# Robustness pass — 2026-09-22

Built, APK signature-verified, and installed on Nebula Capsule 3 D2425 over wireless ADB.

## Device checks passed

- `robustness_test.py`: wrong PIN, crossed and incomplete corners, invalid types, overlong prompt, negative/duplicate/oversized/incomplete HTTP content lengths, malformed JSON, method mismatch, media traversal/missing file, 24 controller reads across eight workers, Unicode byte counts, and restoration of the previous mapping.
- `media_test.py`: deliberately corrupt MP4 reports an error; valid media recovers; factory-camera interruption resumes playback without another play command; stop returns to mapping; a force-stop/relaunch preserves the PIN and mapping.
- Browser controller loaded and displayed the current video, both album choices, coverage and held-out calibration error.
- Recent device logs checked after tests contained no AndroidRuntime fatal exception or CapsuleHttp error.

## Calibration and demo

A fresh 38-pattern internal-camera run completed in `build/album-robust-20260922`. The revised registration did not use a camera ROI or prior manual homography. It produced 137 SIFT inliers and 56,517 accepted dense points. Training RMS was 2.564 projector pixels; spatially interleaved held-out RMS was 2.557. Artwork coverage was 91.275%. These are numerical residuals, not total optical accuracy.

The projected outline was photographed and inspected. A new 384-frame, 16-second loop was rendered, encoded, hash-checked over ADB, and deployed as `life-and-love-calibrated.mp4`, with its calibration report alongside it. Physical playback photos are retained under the run directory; the first captured the dark opening, and subsequent photos captured illuminated phases. The factory green success label belongs to the capture UI.

`check_guards.py` passed: missing/incomplete/changed capture sessions rejected; existing run directories and calibrations protected; unsafe media deployment filenames rejected. Failed calibration output stays in a pending directory rather than replacing a usable map.

## Remaining scope

Calibration and rendering run on the laptop using the supplied project; the Android app plays and controls the result. The renderer is album-specific. The factory sensor provides interrupting still photographs, so there is no continuous movement detection. Physical movement, focus or keystone changes invalidate the map and require a fresh capture and render. The lower portion of this sleeve remains outside the projector beam. The local controller currently belongs to MainActivity's lifetime, rather than an independent Android service; reopening the app restores it after process termination.


## Skill workers and projector-local batch (2026-09-22)

Four skills in `skills/` passed the skill validator and were installed under `~/.codex/skills/`. Three independent album agents exercised the animation skill against existing Life, Hox and Crimson previews, inspected the actual images, and recorded reports in `build/skill-validation/`. No claim of newly authored choreography or external-provider model benchmarking is made. The new pipeline exercised concurrent previews, checksummed reuse, corrupt-frame repair, custom modules, and stale-source rejection; it did not rerender the production video.

A full native-pattern sweep in `build/projector-batch-full` collected all 38 raw JPEGs on the projector in 85.374 seconds; verified local import finished in 90.644 seconds. The importer rejected corrupt data and unsafe archives in offline tests and keeps partial batches ineligible for calibration. Three new maps passed held-out RMS checks at 2.081, 1.780, 1.704 projector pixels. The projected outline photo was inspected and retained in `build/projector-batch-mapping-check`; numerical fits are not optical accuracy guarantees.

Follow-up single capture encountered vendor `VIDIOC_S_FMT: Device or resource busy` twice and later recovered without stopping unrelated services or changing device settings. Treat this as a remaining vendor-camera availability limitation; incomplete captures fail instead of being admitted as calibration data. The original three-sleeve media remains the selected production show.

Final cleanup smoke: two captures completed in 4.587 seconds plus one successful follow-up single photo; shared on-device lock now excludes single/batch capture races across ADB aliases and laptops. Device runner failures are surfaced with retained diagnostic paths.
