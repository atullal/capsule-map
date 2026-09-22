"""Offline integrity tests for the device-bundle importer."""
import hashlib
import json
import pathlib
import tarfile
import tempfile
import unittest
import cv2
import numpy as np
from batch import import_bundle


class BatchImportTests(unittest.TestCase):
    def fixture(self, base, corrupt=False):
        device = base / 'source' / 'capture-test'
        (device / 'shots').mkdir(parents=True)
        (device / 'metadata.json').write_text(json.dumps({'pattern_count': 2}))
        (device / 'patterns.txt').write_text('white\nblack\n')
        (device / 'status').write_text('partial\n')
        records = ['name\tstart_ms\tend_ms\tbytes\tsha256']
        for i, name in enumerate(['white', 'black']):
            frame = np.full((720, 1280, 3), 255 if name == 'white' else 0, np.uint8)
            frame[0:100, 0:100] = 125
            path = device / 'shots' / (name + '.jpg')
            cv2.imwrite(str(path), frame)
            content = path.read_bytes()
            records.append(f'{name}\t{i*1000}\t{(i+1)*1000}\t{len(content)}\t{hashlib.sha256(content).hexdigest()}')
        (device / 'timings.tsv').write_text('\n'.join(records))
        if corrupt:
            with (device / 'shots/white.jpg').open('ab') as handle:
                handle.write(b'corrupt')
        bundle = base / 'batch.tar'
        with tarfile.open(bundle, 'w') as archive:
            archive.add(device, arcname=device.name)
        run = base / 'imported'
        run.mkdir()
        return bundle, run

    def test_partial_is_not_calibration_and_rotation_is_correct(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, run = self.fixture(pathlib.Path(temp))
            result = import_bundle(bundle, run)
            self.assertEqual(result['status'], 'partial')
            self.assertFalse(json.loads((run / 'ai-input.json').read_text())['calibration_ready'])
            upright = cv2.imread(str(run / 'shots/white.png'))
            self.assertLess(float(upright[-50:, -50:].mean()), 150)
            self.assertGreater(float(upright[:50, :50].mean()), 250)

    def test_corruption_rejected_without_complete_session(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, run = self.fixture(pathlib.Path(temp), corrupt=True)
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                import_bundle(bundle, run)
            self.assertFalse((run / 'session.json').exists())

    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            bundle = base / 'unsafe.tar'
            with tarfile.open(bundle, 'w') as archive:
                item = tarfile.TarInfo('../escape')
                archive.addfile(item)
            run = base / 'imported'
            run.mkdir()
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                import_bundle(bundle, run)
            self.assertFalse((base / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
