#!/usr/bin/env bash
set -euo pipefail
SDK_ROOT="${ANDROID_HOME:-/tmp/android-sdk}"
BT="$SDK_ROOT/build-tools/35.0.0"
PLATFORM="$SDK_ROOT/platforms/android-35/android.jar"
mkdir -p build/classes build/dex
# ECJ supports compilation when this runtime has a JRE without javac.
java -jar "${ECJ_JAR:-/tmp/ecj.jar}" -1.8 -bootclasspath "$PLATFORM" -d build/classes src/dev/atul/capsulemap/MainActivity.java
"$BT/aapt2" link -o build/base.apk --manifest AndroidManifest.xml -I "$PLATFORM"
"$BT/d8" --min-api 26 --lib "$PLATFORM" --output build/dex build/classes/dev/atul/capsulemap/*.class
cp build/base.apk build/CapsuleMap-unsigned.apk
(cd build/dex && zip -q -u ../CapsuleMap-unsigned.apk classes.dex)
"$BT/zipalign" -f 4 build/CapsuleMap-unsigned.apk build/CapsuleMap-aligned.apk
if [ ! -f build/debug.keystore ]; then keytool -genkeypair -v -keystore build/debug.keystore -storepass android -keypass android -alias capsule -keyalg RSA -keysize 2048 -validity 3650 -dname 'CN=Capsule Map debug' >/dev/null 2>&1; fi
"$BT/apksigner" sign --ks build/debug.keystore --ks-key-alias capsule --ks-pass pass:android --key-pass pass:android --out CapsuleMap.apk build/CapsuleMap-aligned.apk
"$BT/apksigner" verify --verbose CapsuleMap.apk
