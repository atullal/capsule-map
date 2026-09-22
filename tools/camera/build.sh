#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
SDK_ROOT="${ANDROID_HOME:-/tmp/android-sdk}"
BT="$SDK_ROOT/build-tools/35.0.0"
PLATFORM="$SDK_ROOT/platforms/android-35/android.jar"
OUT=build/camera-bridge
mkdir -p "$OUT/classes" "$OUT/dex"
java -jar "${ECJ_JAR:-/tmp/ecj.jar}" -1.8 -bootclasspath "$PLATFORM" -d "$OUT/classes" tools/camera/CaptureActivity.java
"$BT/aapt2" link -o "$OUT/base.apk" --manifest tools/camera/AndroidManifest.xml -I "$PLATFORM"
"$BT/d8" --min-api 26 --lib "$PLATFORM" --output "$OUT/dex" "$OUT/classes/dev/atul/camerabridge/CaptureActivity.class"
cp "$OUT/base.apk" "$OUT/unsigned.apk"
(cd "$OUT/dex" && zip -q -u ../unsigned.apk classes.dex)
"$BT/zipalign" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$BT/apksigner" sign --ks build/debug.keystore --ks-key-alias capsule --ks-pass pass:android --key-pass pass:android --out "$OUT/CapsuleCameraBridge.apk" "$OUT/aligned.apk"
"$BT/apksigner" verify "$OUT/CapsuleCameraBridge.apk"
