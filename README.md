# Capsule Map prototype

A sideloadable Android TV app for Nebula Capsule 3. The phone controller is a web page served locally by the projector, so an iPhone or Android phone needs no separate installation.

## Install and use

1. Install `CapsuleMap.apk` onto the projector. With Android developer options and ADB enabled, use `adb install -r CapsuleMap.apk` from a computer connected to the same network or USB. If using wireless ADB, first pair/connect the projector with its displayed address. Alternatively transfer the APK with a trusted file transfer method and open it in a file manager after enabling installation from that source.
2. Launch **Capsule Map** from Apps. Allow camera permission when prompted. The status on the projector reports Camera2 enumeration and whether the first enumerated camera opened.
3. Put the phone on the same Wi-Fi and open `http://PROJECTOR_IP:8765` in Safari or Chrome. The projector shows the IP and six-digit PIN. Guest or isolated Wi-Fi may block peer connections.
4. Enter the PIN, drag the corners to fit a physical flat quadrilateral, choose a prompt, and tap **Project**. Tap the remote center button to toggle mapping guides.

The app maps generated 2D animation into a four-corner quadrilateral using a projective transform. It does not scan geometry. A manual mesh endpoint now renders small 3D meshes into the mapped plane; see the manual test below. Prompt matching selects built-in effects; there is no network AI backend or text-to-3D generator. The camera test enumerates Camera2 IDs and attempts to open the first; an opened camera does **not** prove it is the projector calibration camera or that frames can be captured. A zero-camera result proves only that Android's public Camera2 API exposes none to this app. The projector's own auto-keystone can further distort the result; set projector position and keystone first, then calibrate the app.

## Build

This project uses only Android platform APIs. Download the Eclipse ECJ 3.38.0 jar from Maven Central into `/tmp/ecj.jar`, or set `ECJ_JAR` to its path, and set `ANDROID_HOME` to your SDK directory. Run `bash build.sh` after installing SDK platform 35 and build-tools 35.0.0. The script compiles with Java 8 compatibility against `platforms/android-35/android.jar`, then package with `aapt2`, `d8`, and `apksigner` from Android SDK build-tools 35.0.0. See `build.sh` for exact commands. Target SDK 28 is intentional for compatibility with older projector firmware and local HTTP; this is a prototype for sideloading, not a Play Store release.

## Internal camera research (tested on Capsule 3 D2425)

Although Camera2 exposes zero cameras, we verified internal-camera still capture through the stock Nebula factory app, invoked by our companion APK. See [camera access notes and capture helper](tools/camera/README.md). This temporarily shows the factory capture screen; continuous capture alongside our projection is not yet implemented.

## Manual 3D mapping test

The app now accepts a small 3D mesh and camera-derived mapping via `POST /scene`. A rotating cube was projected and verified through the internal sensor and laptop webcam. See [manual workflow, API, and limitations](tools/mapping/README.md). This establishes planar image-based mapping with a 3D rendered scene; AI generation and reconstruction of nonplanar surfaces remain future work.

## Robust playback and calibration workflow

The phone controller now lists staged album videos and can start them or return to effects. `/state` includes actual media status and errors, plus calibration metrics when the video has an attached report. The six-digit PIN persists across app restarts. Videos resume after temporary backgrounding; missing or undecodable media has a retry/return screen. Playback uses the native framebuffer size without reapplying the manual corner warp.

The local HTTP transport limits request bodies to 256 KiB, headers to 16 KiB, and worker/queue counts; it rejects malformed lengths and incomplete bodies with JSON errors. Mapping changes are validated completely and serialized with rendering before they are applied. Crossed/degenerate quadrilaterals are rejected on both mapping endpoints. Controller errors include the server's reason, and guide toggles preserve the current scene mode.

The dense calibration workflow now uses isolated capture sessions, checksummed inputs, coarse surface fitting with cubic re-admission from the supplied projection-mapping project, held-out error checks, and photo-bound visual verification. See [album calibration and deployment](tools/album/README.md). This remains a laptop-driven workflow; it does not yet perform autonomous calibration or AI generation inside the Android app.

Integration checks on the device:

```sh
python3 tools/robustness_test.py --host PROJECTOR_IP --pin PROJECTOR_PIN
```

These checks briefly change the effect prompt and restore the saved mapping. Run while not capturing calibration patterns. Edit the controller in `web/controller.html`; `build.sh` embeds it into the platform-only APK.

## Reusable animation agents and local calibration

Installed skills are maintained in `skills/`: `vinyl-artwork`, `vinyl-animation`, `vinyl-show-parallel`, and `nebula-calibration`. They provide file/command contracts usable by lighter models without depending on a particular provider. Each album agent owns its code/masks/previews; one coordinator owns the projector and final assembly. Their discoverable installations are under `~/.codex/skills/`.

`tools/triptych/parallel.py` renders independent album layers concurrently, fingerprints inputs, resumes valid frames, and combines completed layers. Preview output cannot be deployed as a full show. See `tools/triptych/README.md` for commands.

`tools/camera/batch.py` starts projector-local structured-light acquisition, then retrieves one verified bundle. A measured 38-photo sweep took 85.4 seconds on-device / 90.6 seconds through local import. The resulting `ai-input.json` and contact sheet give an agent a small entry point to the complete photo set. See `tools/camera/README.md` for prerequisites and limitations.
