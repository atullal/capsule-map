# Capsule Map

An Android TV projection-mapping prototype for the **Nebula Capsule 3 (D2425)**, with a local phone/browser controller, internal-sensor calibration capture, and artwork-aware vinyl animations.

The tested workflow projects structured light, captures the projector's internal camera, fits each sleeve independently, renders light along its printed features, and plays one prewarped video on the projector. Reusable agent skills support separate album workers and parallel rendering.

## What works

- Browser controller with a persistent six-digit PIN, manual quad mapping, built-in effects, small 3D mesh scenes, and local video selection.
- Internal-camera JPEG capture through the stock Nebula factory app and a small bridge APK. An opaque overlay hides the factory photo preview.
- Projector-local batch acquisition: 38 native Gray-code patterns, raw photo checksums, timings, and one downloaded archive.
- Dense surface fitting, held-out error checks, and photographed outline verification.
- Independent album workers with cached frames, resumable rendering, input fingerprints, and final composition.
- Demonstrated animations for Skinshape **Life & Love**, Black Market Brass **Hox**, and King Crimson **In the Court of the Crimson King**.

The full capture sweep measured **85.4 seconds on-device / 90.6 seconds through laptop import**. Numerical mapping checks and projected outlines were inspected for all three sleeves. See [validation notes](tools/ROBUSTNESS.md).

## Project structure

```text
AndroidManifest.xml            Main Android application manifest
build.sh                       Platform-only APK build (no Gradle)
src/dev/atul/capsulemap/       Controller server, projection, media and capture overlay
web/controller.html            Browser controller source, embedded during build
tools/camera/                  Bridge APK, single/batch capture, bundle validation
tools/album/                   Single-sleeve calibration, verification and deployment
tools/triptych/                Multi-sleeve registration and parallel animation workers
tools/mapping/                 Manual mesh and camera-to-projector utilities
skills/                        Four reusable agent workflows
vendor/projection-mapping/     Required MIT-licensed calibration/animation helpers
requirements.txt               Host image-processing dependencies
build/                         Generated local artifacts (gitignored)
```

See [step-by-step setup and troubleshooting](docs/SETUP.md), [architecture and data flow](docs/ARCHITECTURE.md), [agent instructions](AGENTS.md), and [contributing](CONTRIBUTING.md).

## Prerequisites

- An authorized ADB connection to the projector, the stock factory app, and the same local network for the browser controller. Internal sensor access is tested on D2425 firmware; other devices may differ.
- macOS or Linux host with Python **3.12+**, Java/JDK, `adb`, `ffmpeg`, `ffprobe`, and `zip`. Host locking uses Unix `fcntl`.
- Android SDK platform **35** and build-tools **35.0.0**.
- Eclipse ECJ **3.38.0** compiler JAR. Obtain it from [Maven Central](https://repo.maven.apache.org/maven2/org/eclipse/jdt/ecj/3.38.0/ecj-3.38.0.jar).

## Build from a fresh clone

```sh
git clone https://github.com/atullal/capsule-map.git
cd capsule-map
python3 -m venv build/mapping-venv
build/mapping-venv/bin/pip install -r requirements.txt

export ANDROID_HOME=/absolute/path/to/android-sdk
export ECJ_JAR=/absolute/path/to/ecj-3.38.0.jar
bash build.sh
bash tools/camera/build.sh
```

Outputs are `CapsuleMap.apk` and `build/camera-bridge/CapsuleCameraBridge.apk`. The main build creates a local debug signing key; build the main APK before the bridge. Keep that key locally if you want later APKs to update an existing installation. APKs and keys are not committed.

Target SDK 28 is intentional for this sideloaded prototype; it is not a Play Store release. All required Python helper sources are bundled; another checkout in the author's home directory is not required. Upstream license and snapshot hashes are in `vendor/projection-mapping/`.

## Install and open the controller

Pair wireless ADB using the pairing address/code displayed by the projector, then connect using its separate debugging address. Commands below use that connected serial:

```sh
adb devices -l
adb -s SERIAL install -r CapsuleMap.apk
adb -s SERIAL install -r build/camera-bridge/CapsuleCameraBridge.apk
adb -s SERIAL shell appops set dev.atul.capsulemap SYSTEM_ALERT_WINDOW allow
adb -s SERIAL shell am start -n dev.atul.capsulemap/.MainActivity
```

Open `http://PROJECTOR_IP:8765` on a phone or laptop on the same network and enter the PIN shown by the app. The phone UI is a local web page; no separate phone app is required. Keep this development service on a trusted local network.

## Capture and calibrate

Keep the projector, sleeves, focus, and keystone fixed. Use a new output directory for each capture:

```sh
build/mapping-venv/bin/python tools/camera/batch.py \
  --serial SERIAL --run build/new-capture --resume-media EXISTING-STAGED-FILE.mp4
```

The projector generates patterns and saves all JPEGs locally before transferring one archive. The client verifies it and writes `session.json`, upright `shots/`, `contact-sheet.jpg`, and `ai-input.json`. Choose an actual staged media file to restore; the demo videos must be rendered locally. `--limit 2` is a partial smoke test, not a usable calibration.

Continue with [single-sleeve calibration](tools/album/README.md) or the [three-sleeve workflow](tools/triptych/README.md). Always inspect a photographed projected outline before accepting new geometry. The three-sleeve example contains arrangement-specific camera ROIs that must be updated when objects move.

## Parallel animation and agent skills

After producing and visually verifying a show calibration:

```sh
build/mapping-venv/bin/python tools/triptych/parallel.py all \
  --run build/YOUR-VERIFIED-SHOW --workers 3 --preview-frames 6 --width 384
```

Omit the preview flags for production frames. Workers can also run individually with `worker --album ID`; a coordinator runs `assemble` and deployment. Custom modules provide `setup(calib_dir)` and `frame_light(seconds)`. See [worker commands and contracts](tools/triptych/README.md).

Agent workflows:

- [vinyl-artwork](skills/vinyl-artwork/SKILL.md): match editions, download references, record provenance.
- [vinyl-animation](skills/vinyl-animation/SKILL.md): feature masks, beat choreography, previews and checks.
- [vinyl-show-parallel](skills/vinyl-show-parallel/SKILL.md): independent album agents and one device-owning coordinator.
- [nebula-calibration](skills/nebula-calibration/SKILL.md): capture, AI inspection, fitting and physical verification.

An agent can read these files directly. For local discovery, copy the desired skill directories into your runtime's skill directory. They are model-neutral file/command workflows; no external AI provider or API key is configured by this repository.

## Verification

Offline checks:

```sh
build/mapping-venv/bin/python tools/camera/test_batch.py
build/mapping-venv/bin/python -m compileall -q tools vendor/projection-mapping
```

Device integration tests are documented in [validation notes](tools/ROBUSTNESS.md). They alter projection temporarily; do not run during calibration capture.

## Current limits and repository contents

Camera2 does not expose this projector's sensor. Capture still uses authorized ADB and vendor factory functionality; it is not continuous camera streaming or a phone-facing capture API. Vendor camera contention can return a temporary busy error. Single captures briefly hold the projected frame; batch calibration displays changing patterns. Failed or partial sessions are rejected.

The app displays 3D meshes, but automatic reconstruction of arbitrary nonplanar objects and prompt-to-3D generation are future work. The existing animations map light to observed sleeves, and animation previews alone do not certify physical alignment.

The public repository includes application code, helpers, skills, tests, and documentation. Room photos, rig-specific maps, downloaded copyrighted album artwork, generated videos, APKs, virtual environments, and signing keys are excluded. Download scripts preserve artwork provenance. The bundled upstream helpers retain their [MIT license](vendor/projection-mapping/LICENSE); that notice applies to those sources.
