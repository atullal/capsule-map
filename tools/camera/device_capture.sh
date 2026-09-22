#!/system/bin/sh
# Run wholly on the projector after one authorized ADB launch. See batch.py.
set -eu
# Binder rejects shared-storage FDs; pipe command output through the shell.
am(){ /system/bin/am "$@" < /dev/null 2>&1 | cat; }
APP=dev.atul.capsulemap
ROOT=/sdcard/Android/data/$APP/files
RUN=${1:?run id required}
RESUME=${2:-three-vinyls.mp4}
LIMIT=${3:-38}
case "$RUN" in ''|*[!A-Za-z0-9_-]*) echo 'Invalid run ID' >&2; exit 2;; esac
case "$RESUME" in ''|*[!A-Za-z0-9._-]*) echo 'Invalid resume file' >&2; exit 2;; esac
case "$LIMIT" in ''|*[!0-9]*) exit 2;; esac
[ "$LIMIT" -ge 1 ] && [ "$LIMIT" -le 38 ] || exit 2
OUT=$ROOT/capture-$RUN
LOCK=$ROOT/capture-batch.lock
mkdir "$LOCK" || { echo 'Capture already running or stale lock' >&2; exit 3; }
mkdir "$OUT" || { rmdir "$LOCK"; exit 3; }
mkdir "$OUT/shots"
SUCCESS=0
setstatus(){ echo "$1" > "$OUT/status.tmp"; mv "$OUT/status.tmp" "$OUT/status"; }
cleanup(){
  trap - EXIT INT TERM
  if [ "$SUCCESS" != 1 ]; then
    am force-stop com.zhixin.factorytest < /dev/null >/dev/null 2>&1 || true
    am start -n "$APP/.MediaActivity" --es file "$RESUME" < /dev/null >/dev/null 2>&1 || true
    sleep .3
    am stopservice -n "$APP/.CaptureGuardService" < /dev/null >/dev/null 2>&1 || true
    setstatus failed
  fi
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
setstatus capturing
START=$(date +%s%3N)
CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '{"schema":1,"run_id":"%s","projector_size":[1920,1080],"camera_size":[1280,720],"step":4,"created_at":"%s","capture_backend":"guarded_factory_jpeg","acquisition":"projector_batch","pattern_count":%s,"raw_rotation_degrees":180}\n' "$RUN" "$CREATED" "$LIMIT" > "$OUT/metadata.json"
printf 'name\tstart_ms\tend_ms\tbytes\tsha256\n' > "$OUT/timings.tsv"
{
  echo white; echo black
  for axis in x y; do for bit in 8 7 6 5 4 3 2 1 0; do echo "${axis}0${bit}p"; echo "${axis}0${bit}n"; done; done
} | head -n "$LIMIT" > "$OUT/patterns.txt"
FACTORY=/sdcard/factorytest/camera_shoot
while read -r pattern; do
  BEGIN=$(date +%s%3N)
  rm -f "$ROOT/capture-pattern-ready"
  am startservice -n "$APP/.CaptureGuardService" --es pattern "$pattern" --es resumeFile "$RESUME" < /dev/null > "$OUT/last-command.log" 2>&1
  n=0
  until [ "$(cat "$ROOT/capture-pattern-ready" 2>/dev/null || true)" = "$pattern" ]; do
    n=$((n+1)); [ "$n" -lt 60 ] || { echo 'Pattern draw timeout' > "$OUT/error.txt"; exit 1; }; sleep .05
  done
  # onDraw acknowledgement plus settling before factory opens/exposes.
  sleep .12
  ls "$FACTORY" 2>/dev/null | sort > "$OUT/before.txt"
  am start -n dev.atul.camerabridge/.CaptureActivity < /dev/null >> "$OUT/last-command.log" 2>&1
  n=0; photo=''
  while [ -z "$photo" ]; do
    ls "$FACTORY" 2>/dev/null | sort > "$OUT/after.txt"
    photo=$(comm -13 "$OUT/before.txt" "$OUT/after.txt" | sed -n '/--calibration_shoot.jpg$/p' | tail -n 1)
    n=$((n+1)); [ "$n" -lt 100 ] || { echo 'Camera JPEG timeout' > "$OUT/error.txt"; exit 1; }; [ -n "$photo" ] || sleep .05
  done
  src=$FACTORY/$photo
  size=0; n=0
  while :; do
    next=$(stat -c %s "$src")
    if [ "$next" = "$size" ] && [ "$size" -gt 0 ]; then break; fi
    size=$next; n=$((n+1)); [ "$n" -lt 40 ] || { echo 'JPEG incomplete' > "$OUT/error.txt"; exit 1; }; sleep .05
  done
  cp "$src" "$OUT/shots/$pattern.jpg"
  # Finish this capture activity to release the sensor, leaving the overlay up.
  input keyevent 4 < /dev/null
  END=$(date +%s%3N)
  HASH=$(sha256sum "$OUT/shots/$pattern.jpg"); HASH=${HASH%% *}
  printf '%s\t%s\t%s\t%s\t%s\n' "$pattern" "$BEGIN" "$END" "$size" "$HASH" >> "$OUT/timings.tsv"
  echo "captured $pattern $((END-BEGIN))ms"
done < "$OUT/patterns.txt"
END=$(date +%s%3N)
printf '{"start_ms":%s,"end_ms":%s,"capture_total_ms":%s}\n' "$START" "$END" "$((END-START))" > "$OUT/summary.json"
rm -f "$OUT/before.txt" "$OUT/after.txt"
# Give the final factory activity time to execute onDestroy/native close.
sleep 1
# Restore before transferring; a local batch never waits on laptop round trips.
am start -n "$APP/.MediaActivity" --es file "$RESUME" < /dev/null >/dev/null
sleep .3
am stopservice -n "$APP/.CaptureGuardService" < /dev/null >/dev/null
if [ "$LIMIT" = 38 ]; then setstatus complete; else setstatus partial; fi
(cd "$ROOT" && tar -cf "capture-$RUN.tar.tmp" "capture-$RUN")
mv "$ROOT/capture-$RUN.tar.tmp" "$ROOT/capture-$RUN.tar"
SUCCESS=1
echo "bundle $ROOT/capture-$RUN.tar"
