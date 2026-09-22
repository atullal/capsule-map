"""Fetch album references with source provenance; independent album agents may run concurrently."""
import argparse
import fcntl
import hashlib
import json
import pathlib
import urllib.request

DEFAULT_SOURCES = {
    'life': {'page': 'https://skinshape.bandcamp.com/album/life-love', 'artwork': 'https://f4.bcbits.com/img/a3113066570_0.jpg'},
    'hox': {'page': 'https://blackmarketbrass.bandcamp.com/album/hox', 'artwork': 'https://f4.bcbits.com/img/a3336206115_0.jpg'},
    'crimson': {'page': 'https://music.apple.com/us/album/in-the-court-of-the-crimson-king-expanded-edition/918534711', 'artwork': 'https://is1-ssl.mzstatic.com/image/thumb/Music5/v4/2f/c7/19/2fc71988-6871-be2c-6731-a3d0f2a6b232/Court_2500px.jpg/1600x1600bb.jpg'},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('build/three-vinyls/reference'))
    parser.add_argument('--album', help='Download only this album key')
    parser.add_argument('--manifest', type=pathlib.Path, help='JSON {album: {page: HTTPS_URL, artwork: HTTPS_JPEG_URL, sha256?: HASH}}')
    args = parser.parse_args()
    sources = json.loads(args.manifest.read_text()) if args.manifest else DEFAULT_SOURCES
    selected = [args.album] if args.album else list(sources)
    args.output.mkdir(parents=True, exist_ok=True)
    for name in selected:
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in name):
            parser.error('album keys must use lowercase letters, digits, _ or -')
        if name not in sources:
            parser.error('album absent from source manifest: ' + name)
        source = dict(sources[name])
        if not all(source.get(k, '').startswith('https://') for k in ('page', 'artwork')):
            parser.error('page and artwork must be HTTPS URLs')
        path = args.output / (name + '.jpg')
        with (args.output / (name + '.lock')).open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            registry = args.output / 'sources.json'
            saved = json.loads(registry.read_text()).get(name, {}) if registry.exists() else {}
            data = path.read_bytes() if path.exists() else b''
            sha = hashlib.sha256(data).hexdigest()
            valid = bool(data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9') and
                         saved.get('artwork') == source['artwork'] and saved.get('sha256') == sha and
                         (not source.get('sha256') or source['sha256'] == sha))
            if not valid:
                request = urllib.request.Request(source['artwork'], headers={'User-Agent': 'CapsuleMap artwork reference downloader'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = response.read(20 * 1024 * 1024 + 1)
                if len(data) > 20 * 1024 * 1024 or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
                    raise RuntimeError('Invalid or oversized JPEG for ' + name)
                sha = hashlib.sha256(data).hexdigest()
                if source.get('sha256') and sha != source['sha256']:
                    raise RuntimeError('Artwork checksum mismatch for ' + name)
                pending = path.with_suffix('.pending')
                pending.write_bytes(data)
                pending.replace(path)
            source['sha256'] = sha
            # Hold the shared registry lock only for the merge; downloads stay parallel.
            with (args.output / '.sources.lock').open('w') as registry_lock:
                fcntl.flock(registry_lock, fcntl.LOCK_EX)
                merged = json.loads(registry.read_text()) if registry.exists() else {}
                merged[name] = source
                pending = registry.with_suffix('.pending')
                pending.write_text(json.dumps(merged, indent=2))
                pending.replace(registry)
            print(name, sha, 'cached' if valid else 'downloaded', flush=True)


if __name__ == '__main__':
    main()
