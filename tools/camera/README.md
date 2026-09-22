# Nebula internal camera: capture without projecting the photo

The D2425 internal Sonix sensor is not enumerated by Camera2. The stock factory app can read `/dev/video0` through its vendor JNI library; our ordinary app and ADB shell cannot open that device directly. Its capture fragment unconditionally puts the resulting bitmap on the projector. There is no supported no-preview argument in the inspected implementation.

The new default path uses a **temporary opaque projection hold**:

1. Capsule Map copies the current video surface in memory using PixelCopy, or copies the current calibration bitmap. For a built-in effect, it draws the current map view into the hold buffer.
2. `CaptureGuardService` places that frame in a full-screen overlay above the factory activity.
3. The existing camera bridge requests mode 3, which saves an actual 1280×720 JPEG. The host watches for a new, complete file and pulls it directly.
4. The factory activity closes, playback resumes, and the hold is removed. The photo is never used as projector content. A watchdog restores the app/removes the hold if the host disappears.

The projection briefly freezes while capture runs; this is **not continuous, fully headless camera streaming**. It avoids the visible factory photograph, green label, white calibration screen and screenshot round-trip. Normal capture no longer restarts the loop at zero. The sensor JPEG is upside-down; `tools/album/snapshot.py` rotates it into camera coordinates.

## Setup

Install the current Capsule Map APK and camera bridge. The projection hold requires Android's draw-over-apps permission. On the development projector, grant it through the already authorized ADB connection:

```sh
adb -s PROJECTOR_IP:PORT shell appops set dev.atul.capsulemap SYSTEM_ALERT_WINDOW allow
```

Open Capsule Map before host capture so its local status endpoint is running. The helper uses a temporary ADB port forward, so it does not need to infer the Wi-Fi IP from an mDNS device serial. It removes the forward afterwards. Concurrent host captures are serialized with a local lock and an atomic on-device lock shared with calibration batches.

```sh
python3 tools/camera/capture.py --serial PROJECTOR_IP:PORT --output build/camera.jpg
build/mapping-venv/bin/python tools/album/snapshot.py --serial PROJECTOR_IP:PORT --output build/camera-upright.png
```

`capture.py` returns the untouched JPEG and timing information. `snapshot.py` preserves playback unless an explicit `--resume FILE --seek-ms POSITION` is supplied. Capture refuses to launch the factory camera unless the projection hold reports ready; it does not silently fall back to projecting a preview.

## Calibration compatibility

`tools/album/capture_patterns.py` now uses the same guarded capture backend. New sessions record `capture_backend: guarded_factory_jpeg`. Registration keeps all usable pixels from these clean images. Older session files and screenshot captures still exclude the factory label's region, preserving compatibility with existing maps. Do not mix the two backends in one session.

The stock factory app and firmware are unchanged. Calibration and rendering still run on the laptop; images remain on the projector and in the selected local output directory. Factory capture has an unavoidable acquisition delay; the hold hides its UI rather than removing that hardware/firmware work.

## Projector-local batch calibration

The fast path generates patterns natively and collects the entire sweep on-device:

```sh
build/mapping-venv/bin/python tools/camera/batch.py --serial PROJECTOR_IP:PORT --run build/new-device-capture --resume-media three-vinyls.mp4
```

After one authorized ADB launch, `device_capture.sh` sequences all 38 patterns locally. The opaque overlay updates in place and the factory activity saves JPEGs behind it. The runner records raw hashes and timings, restores playback, and packages one TAR. The laptop only polls status during acquisition, then downloads that one bundle. No pattern PNGs are uploaded and no per-photo laptop commands or downloads occur.

The importer checks pattern order, inventory, raw hashes, JPEG completeness and dimensions before publishing a complete `session.json`. It writes upright PNGs, a contact sheet, and `ai-input.json` pointing the AI to the room photo and calibration files. These are immediately available to the current agent; automatic upload to a separate model provider is not configured. `--limit 2` produces a partial smoke-test session; it is never accepted as calibration. `--bundle PATH` imports a saved TAR offline. A receipt retains remote paths for recovery.

On-device acquisition was verified with 38 photos in **85.374 seconds**, and **90.644 seconds total** including launch, bundle transfer, checksum verification and PNG conversion. This removes coordination overhead, not the roughly two-second vendor sensor capture delay. Pattern collection is serial; per-surface fitting and animation work can run independently afterward.

The development transport is authenticated ADB. This is not yet a phone-facing capture API, and the app still cannot read the camera directly through public Camera2. The runner's 14-second per-pattern overlay watchdog restores output if acquisition stalls; failed sessions retain diagnostics. Avoid concurrent single captures or changing media while a batch owns the device.

Offline importer validation: `build/mapping-venv/bin/python tools/camera/test_batch.py`.

The final cleanup smoke passed (two photos, then an immediate single capture). A transient vendor camera-busy failure was observed during follow-up validation; incomplete captures remain rejected. Runner exits now report errors promptly, including competing capture ownership.
