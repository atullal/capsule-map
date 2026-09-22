# Manual internal-camera → mapped 3D scene test

Verified on the user's Capsule 3 D2425 on 2026-09-22.

## Workflow

1. Capture the internal sensor through `tools/camera/capture.py`. For this manual workflow, first stage and display a white 1920×1080 PNG. The current guarded capture preserves the displayed image; it no longer projects a factory white screen automatically.
2. Inspect the image rotated 180 degrees. Select the four white-rectangle corners (TL, TR, BR, BL), then four target points on the same flat wall inside that rectangle.
3. `from_camera.py` computes the camera-image-to-normalized-projector homography and writes a scene payload plus an annotated selection image.
4. `send.py` sends the mesh and mapping to the running app over LAN using its displayed PIN.
5. Verify on the actual wall. The factory default capture mode also captured the projected cube in its sensor preview; this is a still-image verification, not a concurrent stream.

## Commands

```sh
python3 -m venv build/mapping-venv
build/mapping-venv/bin/pip install -r tools/mapping/requirements.txt
python3 tools/camera/capture.py --serial PROJECTOR_IP:ADB_PORT --output build/camera.jpg
build/mapping-venv/bin/python tools/mapping/from_camera.py \
  --image build/camera.jpg \
  --calibration '[[432,179],[949,189],[962,481],[410,471]]' \
  --target '[[490,225],[890,233],[899,426],[476,418]]' \
  --output build/manual-mapping
python3 tools/mapping/send.py --host http://PROJECTOR_IP:8765 --pin DISPLAYED_PIN build/manual-mapping/scene.json
python3 tools/mapping/smoke_test.py --host http://PROJECTOR_IP:8765 --pin DISPLAYED_PIN
```

The listed corner numbers are from this test's image, not reusable calibration values. Recapture and select new points whenever projector position, system keystone, zoom, or target plane changes.

## App protocol

POST `/scene` with JSON containing `pin`, `corners` (eight normalized floats in TL/TR/BR/BL order), `guides`, and `scene`:

- `name`: up to 80 characters
- `vertices`: 4–128 xyz vertices, coordinates within ±1.5
- `faces`: 1–256 faces, each 3–8 valid vertex indices
- `color`: Android color string, e.g. `#42ddff`
- `speed`: rotation radians/second, within ±2

The HTTP body limit is 256 KiB; small scene payloads are still recommended. `/state` returns mode, scene, mapping, and guide state. `/update` remains the effect controller; submitting a prompt switches back to the original effects. Scene and mapping persist across app restarts; the PIN persists across app restarts.

The renderer rotates 3D vertices, applies a perspective projection, shades faces, sorts faces by depth, and maps the rendered scene into the wall quad. This simple CPU renderer is intended for small convex meshes such as the demo cube. It is not a general glTF renderer and lacks a depth buffer for intersecting/complex geometry.

## Verification completed

- Signed APK built and installed wirelessly.
- Fresh 1280x720 internal-camera calibration image used to compute the submitted coordinates.
- Cube mesh plus mapping accepted over Wi-Fi and rendered on the projector.
- Laptop webcam showed the cube physically projected inside its guide boundary.
- Nebula's internal camera subsequently captured the cube and mapped border too.
- Invalid PIN, out-of-range face index, and crossed mapping corners rejected without state mutation.
- Scene, mapping, and guide state survived force-stop/relaunch.
- A temporary Wi-Fi interruption occurred; connectivity recovered and checks then passed.

Evidence resides under ignored `build/manual-mapping/`: `selection.jpg`, `scene.json`, `calibration.json`, `mesh-a.png`, `wall-webcam.jpg`, and `internal-camera-mesh.png`. The calibration round-trip residual only checks numerical consistency; it does not measure real-world accuracy.

## What this establishes

An internal-camera image can drive a planar mapping transform, and a manually supplied 3D mesh can be projected into that region. No AI backend or companion app is implemented. This does not reconstruct wall depth, calibrate lens distortion, infer a metric 3D room, or map an arbitrary nonplanar object. Those require additional geometry/calibration work. The guarded capture briefly holds the projected frame and hides the factory preview; it is not a simultaneous live camera stream.

## Patterned-surface test: record sleeve

A second test used the internal camera to locate a record sleeve in front of window blinds. The app now supports `POST /update` with `prompt: "calibration markers"` to display 15 known ArUco 4x4/50 tiles on a black full frame. Tile centers are `(column+1)/6, (row+1)/4` for five columns and three rows. Android renders the six-cell marker surrounded by one white cell of padding; cell size is `min(width/80,height/48)`.

Automatic marker decoding failed on the printed sleeve because surface texture disrupted the pattern. Nine marker centers on the sleeve were manually matched to their known projector positions, then fitted using a homography (approximately 0.5–2.6 camera-pixel fitting residual; this is not an independent accuracy measurement). Points on the blinds and plants were excluded because they lie on different planes.

A cube was sent to the reachable part of the sleeve face, verified in a second internal-camera capture, and left running with guides hidden. Existing ink remains visible through projected colors. Local evidence and exact correspondences are in ignored `build/sleeve-mapping/`. This is an agent-assisted mapping workflow, not autonomous marker recognition or depth reconstruction.
