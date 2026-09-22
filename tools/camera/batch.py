"""Run calibration acquisition on the projector, then import one verified photo bundle.

No AI or per-photo laptop round trips occur during acquisition. Requires the current
Capsule Map APK, bridge, overlay permission, and an authorized ADB connection.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import tarfile
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
REMOTE = '/sdcard/Android/data/dev.atul.capsulemap/files'


def pattern_names():
    return ['white', 'black'] + [f'{axis}{bit:02d}{sign}' for axis in 'xy'
                                for bit in range(8, -1, -1) for sign in 'pn']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_bundle(bundle, run, serial='unknown'):
    """Validate all raw bytes before publishing a usable calibration session."""
    import cv2
    import numpy as np
    run = pathlib.Path(run)
    raw = run / 'device'
    raw.mkdir(exist_ok=False)
    with tarfile.open(bundle) as archive:
        for member in archive.getmembers():
            target = (raw / member.name).resolve()
            if not target.is_relative_to(raw.resolve()) or not (member.isfile() or member.isdir()):
                raise RuntimeError('Unsafe archive member: ' + member.name)
        archive.extractall(raw, filter='data')
    candidates = list(raw.rglob('metadata.json'))
    if len(candidates) != 1:
        raise RuntimeError('Bundle must contain exactly one metadata.json')
    device = candidates[0].parent
    metadata = json.loads(candidates[0].read_text())
    status = (device / 'status').read_text().strip()
    names = (device / 'patterns.txt').read_text().split()
    if len(names) != len(set(names)) or names != pattern_names()[:len(names)] or not names:
        raise RuntimeError('Unexpected pattern inventory/order')
    if metadata.get('pattern_count') != len(names):
        raise RuntimeError('Metadata pattern count differs')
    records = {}
    for line in (device / 'timings.tsv').read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'name':
            continue
        if len(fields) != 5:
            raise RuntimeError('Malformed timing record')
        name, start, end, size, sha = fields
        if int(end) < int(start) or int(size) <= 0:
            raise RuntimeError('Invalid capture timing or size')
        if name in records or name not in names:
            raise RuntimeError('Duplicate or unexpected capture')
        photo = device / 'shots' / (name + '.jpg')
        if not photo.is_file() or photo.stat().st_size != int(size) or digest(photo) != sha:
            raise RuntimeError('Raw capture checksum failed: ' + name)
        data = photo.read_bytes()
        if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
            raise RuntimeError('Truncated JPEG: ' + name)
        records[name] = {'start_ms': int(start), 'end_ms': int(end), 'bytes': int(size), 'sha256': sha}
    if set(records) != set(names) or status not in ('complete', 'partial'):
        raise RuntimeError('Incomplete device batch: ' + status)
    shots = run / 'shots'
    shots.mkdir(exist_ok=False)
    hashes = {}
    tiles = []
    for name in names:
        image = cv2.imread(str(device / 'shots' / (name + '.jpg')))
        if image is None or image.shape != (720, 1280, 3):
            raise RuntimeError('Invalid camera dimensions: ' + name)
        image = cv2.rotate(image, cv2.ROTATE_180)
        out = shots / (name + '.png')
        if not cv2.imwrite(str(out), image):
            raise RuntimeError('Cannot write ' + str(out))
        hashes[name] = digest(out)
        tile = cv2.resize(image, (320, 180))
        tile = cv2.copyMakeBorder(tile, 24, 0, 0, 0, cv2.BORDER_CONSTANT)
        cv2.putText(tile, name, (8, 17), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
        tiles.append(tile)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(run / 'contact-sheet.jpg'), np.vstack([np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)]))
    complete = names == pattern_names() and status == 'complete'
    session = {'schema': 1, 'serial': serial, 'created_at': metadata.get('created_at', datetime.datetime.now(datetime.timezone.utc).isoformat()),
               'status': 'complete' if complete else 'partial', 'capture_backend': 'guarded_factory_jpeg',
               'acquisition': 'projector_batch', 'camera_size': [1280, 720], 'projector_size': [1920, 1080],
               'patterns': names, 'shots': hashes, 'device': metadata, 'timings': records,
               'bundle_sha256': digest(pathlib.Path(bundle)),
               'acquisition_seconds': (max(r['end_ms'] for r in records.values())-min(r['start_ms'] for r in records.values()))/1000}
    (run / 'session.json').write_text(json.dumps(session, indent=2))
    # Small, explicit entry point for vision agents; full-resolution photos remain adjacent.
    packet = {'session': 'session.json', 'overview': 'contact-sheet.jpg', 'room_photo': 'shots/white.png',
              'dark_photo': 'shots/black.png' if 'black' in names else None,
              'calibration_ready': complete, 'coordinate_system': 'Upright camera, 1280x720; projector, 1920x1080',
              'next_step': 'Decode Gray patterns and fit each surface, then photograph projected outlines for visual verification.',
              'notes': 'Photos and raw checksums were collected locally on the projector. No cloud upload performed.'}
    (run / 'ai-input.json').write_text(json.dumps(packet, indent=2))
    return session


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', required=True)
    p.add_argument('--run', type=pathlib.Path, required=True)
    p.add_argument('--resume-media', default='three-vinyls.mp4')
    p.add_argument('--limit', type=int, default=38, help='Fewer than 38 is a smoke test, not a usable calibration')
    p.add_argument('--timeout', type=float, default=300)
    p.add_argument('--bundle', type=pathlib.Path, help='Import an already downloaded bundle without contacting the projector')
    a = p.parse_args()
    if not 1 <= a.limit <= 38:
        p.error('--limit must be 1..38')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', a.resume_media):
        p.error('--resume-media must be a plain staged filename')
    a.run = a.run.resolve()
    a.run.mkdir(parents=True, exist_ok=False)
    if a.bundle:
        print(json.dumps(import_bundle(a.bundle.resolve(), a.run, a.serial), indent=2))
        return
    def adb(*args):
        result = subprocess.run(['adb', '-s', a.serial, *args], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout.strip()
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    device = REMOTE + '/capture-' + run_id
    runner = '/data/local/tmp/capsule-device-capture.sh'
    started = time.monotonic()
    adb('push', str(HERE / 'device_capture.sh'), runner)
    exit_file = '/data/local/tmp/capsule-capture-' + run_id + '.exit'
    log_file = '/data/local/tmp/capsule-capture-' + run_id + '.log'
    invocation = 'sh ' + ' '.join(shlex.quote(v) for v in [runner, run_id, a.resume_media, str(a.limit)])
    invocation += '; result=$?; echo "$result" >' + shlex.quote(exit_file)
    command = 'nohup sh -c ' + shlex.quote(invocation) + ' >' + shlex.quote(log_file) + ' 2>&1 </dev/null &'
    adb('shell', command)
    receipt = {'serial': a.serial, 'run_id': run_id, 'remote_directory': device, 'remote_bundle': device + '.tar',
               'remote_exit': exit_file, 'remote_log': log_file}
    (a.run / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    print('Projector is collecting the batch locally:', run_id, flush=True)
    deadline = started + a.timeout
    last = None
    while time.monotonic() < deadline:
        # A single lightweight status poll, never a per-photo download/command sequence.
        report = adb('shell', 'if [ -f ' + shlex.quote(device + '/status') + ' ]; then cat ' + shlex.quote(device + '/status') + '; fi')
        if report != last and report:
            print('Device:', report, flush=True)
            last = report
        if report in ('complete', 'partial'):
            ready = adb('shell', 'if [ -f ' + shlex.quote(device + '.tar') + ' ]; then echo ready; fi')
            if ready == 'ready':
                break
        if report.startswith('failed'):
            detail = adb('shell', 'cat ' + shlex.quote(device + '/error.txt') + ' 2>/dev/null || true')
            raise RuntimeError('Device batch failed: ' + detail + '; diagnostics retained at ' + device)
        exited = adb('shell', 'cat ' + shlex.quote(exit_file) + ' 2>/dev/null || true')
        if exited and exited != '0':
            detail = adb('shell', 'tail -n 8 ' + shlex.quote(log_file))
            raise RuntimeError('Device runner exited ' + exited + ': ' + detail)
        time.sleep(2)
    else:
        raise TimeoutError('Batch not complete; receipt.json identifies the retained device run. Device watchdog restores playback.')
    bundle = a.run / 'capture.tar'
    adb('pull', device + '.tar', str(bundle))
    session = import_bundle(bundle, a.run, a.serial)
    session['total_seconds'] = time.monotonic() - started
    (a.run / 'session.json').write_text(json.dumps(session, indent=2))
    print(json.dumps({'run': str(a.run), 'status': session['status'], 'photos': len(session['shots']),
                      'acquisition_seconds': session['acquisition_seconds'], 'total_seconds': session['total_seconds'],
                      'ai_input': str(a.run / 'ai-input.json')}, indent=2))


if __name__ == '__main__':
    main()
