# Architecture and data flow

## Projector application

`MainActivity` owns the local HTTP server and mapped effect/mesh view. `LocalHttp` bounds requests and serializes UI mutations. `MediaActivity` plays prewarped 1920×1080 media without applying a second warp. Edit the browser UI in `web/controller.html`; the build embeds it into Java.

`CaptureGuardService` draws an opaque overlay above the factory app. It copies the active projection for a single photo or generates native STEP=4 Gray patterns for calibration. `CaptureActivity` in the bridge APK invokes the vendor factory capture fragment, which reads the internal sensor and saves a 1280×720 JPEG. The sensor's public Camera2 interface is unavailable on the tested device.

## Batch capture and AI handoff

1. The host launches `tools/camera/device_capture.sh` through authenticated ADB.
2. The runner owns an atomic device capture lock, displays each pattern, waits for a new JPEG, copies it into the session, and records its checksum and timing.
3. After all 38 patterns, it restores the selected media and creates one TAR archive. The overlay has a recovery watchdog.
4. `tools/camera/batch.py` downloads the archive, verifies inventory and bytes, rotates photos 180 degrees, and publishes a complete session only after validation.
5. `ai-input.json` points the agent to the contact sheet and full-resolution photos. No cloud upload is implicit.

Fitting and rendering currently execute on the host. The complete raw batch remains on the projector. Failed sessions retain diagnostics and cannot be used for calibration.

## Calibration and animation

Reference artwork is registered to the camera photo. Relative-contrast Gray decoding supplies dense camera-to-projector samples. A homography with cubic residual fitting models sleeve bowing; held-out samples check prediction error. A photographed edge projection supplies separate physical verification.

Each album worker returns a 1400×1400 floating BGR illumination frame. It applies its calibrated projector lookup exactly once. Independent workers write isolated checksummed frames and fingerprints. The coordinator combines the layers with black gaps, encodes an H.264 loop, checks the device transfer hash, and starts playback. Native media playback avoids a runtime warp per video frame.

## Ownership and retained artifacts

Only one coordinator controls the projector/camera. Other agents can research artwork, create masks and animation code, and render separate albums concurrently. Workers consume a fixed calibration snapshot; any physical movement invalidates its current alignment claim.

Code and documentation are tracked. `build/` holds local sessions, photos, calibration maps, previews, video, and debug signing keys. These artifacts are intentionally separate from the public source tree. Required upstream Python modules are vendored with their license and exact file hashes.
