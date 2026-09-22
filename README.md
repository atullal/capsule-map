# Capsule Map prototype

A sideloadable Android TV app for Nebula Capsule 3. The phone controller is a web page served locally by the projector, so an iPhone or Android phone needs no separate installation.

## Install and use

1. Install `CapsuleMap.apk` onto the projector. With Android developer options and ADB enabled, use `adb install -r CapsuleMap.apk` from a computer connected to the same network or USB. If using wireless ADB, first pair/connect the projector with its displayed address. Alternatively transfer the APK with a trusted file transfer method and open it in a file manager after enabling installation from that source.
2. Launch **Capsule Map** from Apps. Allow camera permission when prompted. The status on the projector reports Camera2 enumeration and whether the first enumerated camera opened.
3. Put the phone on the same Wi-Fi and open `http://PROJECTOR_IP:8765` in Safari or Chrome. The projector shows the IP and six-digit PIN. Guest or isolated Wi-Fi may block peer connections.
4. Enter the PIN, drag the corners to fit a physical flat quadrilateral, choose a prompt, and tap **Project**. Tap the remote center button to toggle mapping guides.

The app maps generated 2D animation into a four-corner quadrilateral using a projective transform. It does not scan geometry or render true 3D objects. Prompt matching selects built-in effects; there is no network AI backend or text-to-3D generator. The camera test enumerates Camera2 IDs and attempts to open the first; an opened camera does **not** prove it is the projector calibration camera or that frames can be captured. A zero-camera result proves only that Android's public Camera2 API exposes none to this app. The projector's own auto-keystone can further distort the result; set projector position and keystone first, then calibrate the app.

## Build

This project uses only Android platform APIs. Download the Eclipse ECJ 3.38.0 jar from Maven Central into `/tmp/ecj.jar`, or set `ECJ_JAR` to its path, and set `ANDROID_HOME` to your SDK directory. Run `bash build.sh` after installing SDK platform 35 and build-tools 35.0.0. The script compiles with Java 8 compatibility against `platforms/android-35/android.jar`, then package with `aapt2`, `d8`, and `apksigner` from Android SDK build-tools 35.0.0. See `build.sh` for exact commands. Target SDK 28 is intentional for compatibility with older projector firmware and local HTTP; this is a prototype for sideloading, not a Play Store release.
