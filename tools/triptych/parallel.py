"""Independent, resumable album workers. No worker accesses the projector.

Custom modules expose setup(calib_dir) and frame_light(seconds), returning a
1400x1400x3 floating-point BGR array in [0, 1] for a 28.8-second, 100 BPM loop.
"""
import argparse
import concurrent.futures
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path('/Users/atullal/Projects/projection-mapping')
ALBUMS = ('life', 'hox', 'crimson')
FPS, FRAMES, LOOP = 30, 864, 28.8


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    pending = path.with_suffix('.pending.json')
    pending.write_text(json.dumps(value, indent=2))
    pending.replace(path)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verification(run):
    metrics = json.loads((run / 'calibration.json').read_text())
    evidence = json.loads((run / 'verification.json').read_text())
    if digest(run / 'edge-verification.png') != evidence['photo_sha256']:
        raise RuntimeError('Outline verification photo changed')
    for name, report in metrics.items():
        if digest(run / name / 'calib/render_map.npz') != report['render_map_sha256']:
            raise RuntimeError('Calibration changed: ' + name)
    return metrics


def settings(args, album):
    run = args.run.resolve()
    source = args.source.resolve()
    calib = run / album / 'calib'
    paths = [HERE / 'parallel.py', HERE / 'crimson.py']
    # Include helper dependencies: a changed mask or source helper invalidates frames.
    paths += sorted(source.glob('*.py'))
    paths += [calib / n for n in ('reference.png', 'sleeve.png', 'covered.png', 'render_map.npz')]
    if args.module:
        paths += sorted(args.module.resolve().parent.glob('*.py'))
    sample_ids = np.linspace(0, FRAMES - 1, args.preview_frames, dtype=int).tolist() if args.preview_frames else list(range(FRAMES))
    value = dict(schema=1, album=album, width=args.width, height=args.width * 9 // 16,
                 fps=FPS, loop_seconds=LOOP, sample_ids=sample_ids,
                 production=not args.preview_frames and args.width == 1920,
                 module=str(args.module.resolve()) if args.module else None,
                 dependencies={str(p): digest(p) for p in paths})
    value['fingerprint'] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def output_dir(args, album):
    return args.run.resolve() / ('previews' if args.preview_frames else 'workers') / album


def animation(args, album, output):
    source = args.source.resolve()
    sys.path.insert(0, str(source))
    import render as warp
    import animkit
    calib = args.run.resolve() / album / 'calib'
    warp.CALIB = animkit.CALIB = str(calib)
    projector_warp = warp.ProjectorWarp()
    if args.module:
        sys.path.insert(0, str(args.module.resolve().parent))
        module = load_module(args.module.resolve(), 'custom_album_animation')
        module.setup(calib)
        return module.frame_light, projector_warp
    if album == 'life':
        import animate
        animate.CALIB = str(calib)
        animate.setup()
        fn = lambda t: animate.frame_light((t % 14.4) * 16 / 14.4)
    elif album == 'hox':
        import animate_hox as hox
        import animate_hox_show as show
        hox.CALIB = str(calib)
        hox.FIELDS = str(output / 'hox_fields.npz')
        cache_key = hashlib.sha256((digest(calib / 'reference.png') + digest(source / 'animate_hox.py') + digest(source / 'animkit.py')).encode()).hexdigest()
        stamp = output / 'hox_fields.sha256'
        if not Path(hox.FIELDS).exists() or not stamp.exists() or stamp.read_text() != cache_key:
            hox.build_fields()
            stamp.write_text(cache_key)
        show.SCENES = [show.ignition, show.radar, show.data_rain, show.spotlights_finale]
        show.TOTAL = LOOP
        show.setup()
        fn = show.frame_light
    elif album == 'crimson':
        module = load_module(HERE / 'crimson.py', 'crimson_animation')
        module.setup(calib / 'reference.png', animkit.beam_alpha())
        return module.frame_light, projector_warp
    else:
        raise RuntimeError('A new album requires --module')
    return lambda t: fn(t) * animkit.smoothstep(t / .6) * (1 - animkit.smoothstep((t - (LOOP - .7)) / .7)), projector_warp


def worker(args):
    cv2.setNumThreads(1)
    verification(args.run.resolve())
    output = output_dir(args, args.album)
    (output / 'frames').mkdir(parents=True, exist_ok=True)
    with (output / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = settings(args, args.album)
        manifest_path = output / 'manifest.json'
        previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        records = previous.get('files', {}) if previous.get('fingerprint') == config['fingerprint'] else {}
        manifest = dict(config, complete=False, files=records)
        atomic_json(manifest_path, manifest)
        light_fn = warp = None
        rendered = reused = 0
        started = time.monotonic()
        for index, sample in enumerate(config['sample_ids']):
            name = f'f{index:04d}.png'
            path = output / 'frames' / name
            if path.exists() and records.get(name) == digest(path):
                reused += 1
                continue
            if light_fn is None:
                light_fn, warp = animation(args, args.album, output)
            light = light_fn(sample / FPS)
            if light.shape != (1400, 1400, 3) or light.dtype.kind != 'f' or not np.isfinite(light).all():
                raise RuntimeError('frame_light must return finite 1400x1400x3 floating BGR')
            if light.min() < -1e-6 or light.max() > 1.000001:
                raise RuntimeError('frame_light out of [0,1] range')
            frame = warp.full(np.uint8(np.clip(light, 0, 1) * 255 + .5))
            if args.width != 1920:
                frame = cv2.resize(frame, (config['width'], config['height']), interpolation=cv2.INTER_AREA)
            pending = path.with_name(path.stem + '.pending.png')
            if not cv2.imwrite(str(pending), frame, [cv2.IMWRITE_PNG_COMPRESSION, 1]):
                raise RuntimeError('Frame write failed')
            pending.replace(path)
            records[name] = digest(path)
            rendered += 1
            atomic_json(manifest_path, manifest)
            if rendered % 72 == 0:
                print(f'{args.album}: {index + 1}/{len(config["sample_ids"])}', flush=True)
        tiles = []
        for i in np.linspace(0, len(config['sample_ids']) - 1, 6, dtype=int):
            tile = cv2.resize(cv2.imread(str(output / 'frames' / f'f{i:04d}.png')), (480, 270))
            cv2.putText(tile, f'{args.album}: {config["sample_ids"][i] / FPS:.2f}s', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            tiles.append(tile)
        cv2.imwrite(str(output / 'contact-sheet.jpg'), np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])]))
        # Never certify a render if inputs changed while another agent was editing them.
        if settings(args, args.album)['fingerprint'] != config['fingerprint']:
            raise RuntimeError('Inputs changed during rendering; rerun this worker')
        manifest.update(complete=True, rendered=rendered, reused=reused, seconds=round(time.monotonic() - started, 3))
        atomic_json(manifest_path, manifest)
        print(json.dumps(dict(album=args.album, output=str(output), rendered=rendered, reused=reused, seconds=manifest['seconds'])), flush=True)


def assemble(args):
    cv2.setNumThreads(1)
    run = args.run.resolve()
    metrics = verification(run)
    albums = args.albums.split(',')
    manifests = []
    for album in albums:
        path = output_dir(args, album) / 'manifest.json'
        manifest = json.loads(path.read_text())
        worker_args = argparse.Namespace(**vars(args))
        worker_args.module = Path(manifest['module']) if manifest['module'] else None
        if not manifest['complete'] or settings(worker_args, album)['fingerprint'] != manifest['fingerprint']:
            raise RuntimeError('Incomplete or stale worker: ' + album)
        manifests.append(manifest)
    config = manifests[0]
    for manifest in manifests[1:]:
        if any(manifest[k] != config[k] for k in ('sample_ids', 'width', 'height', 'production')):
            raise RuntimeError('Worker frame timelines or resolutions differ')
    output = run if config['production'] else run / 'preview'
    (output / 'frames').mkdir(parents=True, exist_ok=True)
    with (output / '.assembly.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (output / 'render.json').unlink(missing_ok=True)
        for index in range(len(config['sample_ids'])):
            frame = np.zeros((config['height'], config['width'], 3), np.uint8)
            for album, manifest in zip(albums, manifests):
                name = f'f{index:04d}.png'
                path = output_dir(args, album) / 'frames' / name
                if digest(path) != manifest['files'].get(name):
                    raise RuntimeError('Corrupt worker frame: ' + str(path))
                layer = cv2.imread(str(path))
                if layer is None or layer.shape != frame.shape:
                    raise RuntimeError('Wrong worker frame dimensions')
                frame = np.maximum(frame, layer)
            if not cv2.imwrite(str(output / 'frames' / f'f{index:04d}.jpg'), frame, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError('Composite write failed')
        verification(run)
        for album, manifest in zip(albums, manifests):
            worker_args = argparse.Namespace(**vars(args))
            worker_args.module = Path(manifest['module']) if manifest['module'] else None
            if settings(worker_args, album)['fingerprint'] != manifest['fingerprint']:
                raise RuntimeError('Inputs changed during assembly: ' + album)
        # Match the established deploy report; previews deliberately have no render.json.
        report = dict(fps=FPS, frames=len(config['sample_ids']), duration_seconds=LOOP,
                      beats=48, frames_per_beat=18, production=config['production'],
                      calibration={album: metrics[album] for album in albums},
                      workers={album: m['fingerprint'] for album, m in zip(albums, manifests)})
        atomic_json(output / ('render.json' if config['production'] else 'preview.json'), report)
    print(json.dumps(dict(assembled=str(output), production=config['production'], frames=report['frames'])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('worker', 'all', 'assemble'))
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--album', default='life')
    parser.add_argument('--albums', default=','.join(ALBUMS))
    parser.add_argument('--module', type=Path)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--preview-frames', type=int, default=0)
    parser.add_argument('--width', type=int, default=1920)
    args = parser.parse_args()
    if args.width < 32 or args.width > 1920 or args.width % 16 or args.preview_frames not in (0, *range(2, FRAMES + 1)):
        parser.error('width must be 32..1920 divisible by 16; preview-frames must be 2..864 or 0')
    if args.width != 1920 and not args.preview_frames:
        parser.error('reduced resolution requires --preview-frames')
    if args.workers < 1 or args.workers > 8:
        parser.error('workers must be 1..8')
    for album in [args.album, *args.albums.split(',')]:
        if not album or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in album):
            parser.error('album names must use lowercase letters, digits, _ or -')
    if args.command == 'worker':
        worker(args)
    elif args.command == 'assemble':
        assemble(args)
    else:
        if args.module:
            parser.error('--module belongs to an individual worker; then use assemble')
        def run_album(album):
            command = [sys.executable, str(Path(__file__).resolve()), 'worker', '--run', str(args.run), '--source', str(args.source), '--album', album, '--width', str(args.width), '--preview-frames', str(args.preview_frames)]
            env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
            subprocess.run(command, check=True, env=env)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(run_album, args.albums.split(',')))
        assemble(args)


if __name__ == '__main__':
    main()
