# Setup: fresh clone to first capture

This guide targets macOS/Linux and the tested Nebula Capsule 3 D2425. Windows users need a Unix environment for the host tools (`fcntl`); native Windows execution is not currently supported. No external AI API account is required for manual calibration or rendering.

Run commands from the repository root. Replace uppercase placeholders with your actual paths or addresses. The private demo photos, maps and movies are not included in a clone.

## 1. Host tools and Python

Install Git, Python 3.12 or later, a JDK that provides `java` and `keytool`, Android SDK command-line/platform tools, FFmpeg, and `zip`. Ensure `adb`, `sdkmanager`, `ffmpeg` and `ffprobe` are on PATH. Java 27 was used during development; other JDKs should be verified with the build on your host.

```sh
git clone https://github.com/atullal/capsule-map.git
cd capsule-map
python3 -m venv build/mapping-venv
build/mapping-venv/bin/python -m pip install -r requirements.txt

java -version
adb version
ffmpeg -version
ffprobe -version
```

The Python environment is intentionally under ignored `build/`. Required upstream Python helper sources are already bundled in `vendor/projection-mapping`.

## 2. Android SDK and compiler

Set `ANDROID_HOME` to the SDK root that contains `platforms/` and `build-tools/`. The command-line-tools directory itself is not necessarily that root.

```sh
export ANDROID_HOME=/absolute/path/to/android-sdk
sdkmanager --sdk_root="$ANDROID_HOME" "platform-tools" "platforms;android-35" "build-tools;35.0.0"
sdkmanager --sdk_root="$ANDROID_HOME" --licenses
```

Review the SDK licenses when prompted. Download the ECJ compiler into the ignored build directory:

```sh
curl --fail --location \
  https://repo.maven.apache.org/maven2/org/eclipse/jdt/ecj/3.38.0/ecj-3.38.0.jar \
  --output build/ecj-3.38.0.jar
export ECJ_JAR="$PWD/build/ecj-3.38.0.jar"
bash build.sh
bash tools/camera/build.sh
```

Build the main APK first: it creates `build/debug.keystore`, also used by the bridge. The two outputs are:

- `CapsuleMap.apk`
- `build/camera-bridge/CapsuleCameraBridge.apk`

Keep the signing key locally to update your installed debug app later. Never commit it. A new machine/key cannot update an APK signed with the old key without an installation migration; uninstalling removes app data, so do not use that as an automatic workaround. Java native-access warnings from SDK tools are distinct from a failed build; check the exit code and APK signature verification.

## 3. Pair wireless ADB and install

Enable developer options and wireless debugging on the projector using the options available in its firmware. Open **Pair device with pairing code**. The pairing endpoint and normal debugging endpoint use different ports and may change between sessions.

```sh
adb pair PROJECTOR_IP:PAIRING_PORT
# Enter the pairing code interactively.
adb connect PROJECTOR_IP:DEBUG_PORT
adb devices -l
export PROJECTOR_SERIAL=PROJECTOR_IP:DEBUG_PORT

adb -s "$PROJECTOR_SERIAL" install -r CapsuleMap.apk
adb -s "$PROJECTOR_SERIAL" install -r build/camera-bridge/CapsuleCameraBridge.apk
adb -s "$PROJECTOR_SERIAL" shell appops set dev.atul.capsulemap SYSTEM_ALERT_WINDOW allow
adb -s "$PROJECTOR_SERIAL" shell am start -n dev.atul.capsulemap/.MainActivity
```

A USB-C cable alone does not establish an authorized ADB transport. Use the serial actually listed as `device`, and consistently select one serial if ADB lists aliases for the same projector.

Open `http://PROJECTOR_IP:8765` on a browser on the same LAN. Enter the six-digit PIN displayed by the app. That PIN is separate from the ADB pairing code. The HTTP server belongs to the running main activity, so open the app first. Guest Wi-Fi/client isolation may prevent access.

## 4. Stage a safe initial image

A fresh installation has no album videos. Create and stage a black PNG as the restore target for initial camera tests:

```sh
build/mapping-venv/bin/python -c "import cv2,numpy as np; assert cv2.imwrite('build/black.png',np.zeros((1080,1920,3),np.uint8))"
adb -s "$PROJECTOR_SERIAL" push build/black.png /sdcard/Android/data/dev.atul.capsulemap/files/black.png
adb -s "$PROJECTOR_SERIAL" shell am start -n dev.atul.capsulemap/.MediaActivity --es file black.png
```

The app must have been launched before staging, so its external files directory exists. These commands intentionally change what is projected.

## 5. Test local capture, then collect a full session

Keep other camera/control tools idle. The smoke test displays white/black patterns, collects two photos on the projector, transfers a verified archive, and restores `black.png`:

```sh
build/mapping-venv/bin/python tools/camera/batch.py \
  --serial "$PROJECTOR_SERIAL" --run build/capture-smoke \
  --limit 2 --resume-media black.png
```

Expected result: `status: partial`, two upright images in `shots/`, a contact sheet, `session.json`, `receipt.json`, and `ai-input.json`. Inspect white/black photos for the intended scene and illumination contrast. A partial session is deliberately ineligible for calibration.

Position sleeves, projector, focus and keystone before the full capture, then keep them fixed:

```sh
build/mapping-venv/bin/python tools/camera/batch.py \
  --serial "$PROJECTOR_SERIAL" --run build/capture-full --resume-media black.png
```

Expected result: `status: complete`, 38 photos. Typical measured duration was about 90 seconds through local import; it is not instantaneous capture. Always choose a new run directory. `receipt.json` identifies the retained on-device run and log if something fails.

## 6. From photos to a show

Read the relevant workflow rather than reusing private demo calibration:

- [Single sleeve](../tools/album/README.md): fit a reference, project its outline, photograph and inspect, record verification, render, deploy.
- [Three sleeves](../tools/triptych/README.md): download matching editions, adapt camera ROIs to your arrangement, fit each cover, verify, run independent album workers and assemble.
- [Camera operation and recovery](../tools/camera/README.md).

`ai-input.json` points an agent to the room photo and pattern set. It does not send anything to an external API. For custom art, the module and print edition must match; renaming an existing animation does not adapt its masks to a new album.

## 7. Optional agent skill installation

Agents can read `skills/*/SKILL.md` directly without installation. To make them discoverable in a local Codex skills directory, copy each directory. The following skips existing entries rather than overwriting customizations:

```sh
skill_destination="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_destination"
for skill in vinyl-artwork vinyl-animation vinyl-show-parallel nebula-calibration; do
  if [ ! -e "$skill_destination/$skill" ] && [ ! -L "$skill_destination/$skill" ]; then
    cp -R "skills/$skill" "$skill_destination/$skill"
  fi
done
```

Other runtimes can consume the Markdown instructions and command contracts directly. Delegation/model selection is done by that runtime; the skills do not connect provider accounts. See [AGENTS.md](../AGENTS.md) for device ownership and verification rules.

## Troubleshooting

| Symptom | Check or next action |
|---|---|
| `android.jar`, `aapt2` or ECJ missing | Check SDK root, required SDK versions and `ECJ_JAR`; use the exports above in the build shell. |
| No authorized ADB device | Reopen wireless debugging, check the current connect port and pairing authorization; verify LAN reachability. |
| Update signature mismatch | Use the original local signing key; preserve app data before deciding on a reinstall. |
| Overlay permission missing | Grant the documented app-op on the development projector and reopen the app. |
| Camera busy / no fresh JPEG | Let the current vendor camera operation finish; inspect retained logs and retry with a fresh run. Do not admit an old JPEG as the new shot. |
| Capture lock exists | Check whether a runner or single capture is active. Never remove an active lock; investigate interrupted-run diagnostics before clearing a confirmed stale lock. |
| Bundle failed or timed out | Inspect `receipt.json` and the remote `status`, `error.txt`, and log. Do not change the session status manually. |
| No media after capture | Verify the exact restore filename is staged, then open it through `MediaActivity`. |
| Reference match/fit rejected | Verify the cover edition, scene contrast, camera ROI and stationary setup. Do not lower thresholds merely to force a result. |
| Renderer refuses verification | Project the outline and actually inspect a current photo, then record the matching evidence. |
| Local control page unavailable | Launch MainActivity, confirm the projector IP and LAN access; the server is not an independent background service. |

For a capture that has ended but left an overlay, the watchdog normally restores output. After confirming no capture is active, the operator can recover the staged image explicitly:

```sh
adb -s "$PROJECTOR_SERIAL" shell am start -n dev.atul.capsulemap/.MediaActivity --es file black.png
adb -s "$PROJECTOR_SERIAL" shell am stopservice -n dev.atul.capsulemap/.CaptureGuardService
```
