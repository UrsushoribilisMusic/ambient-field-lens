import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from weights_cpu import verify_files
from corpus_cpu import collect_manuals, scrub_credentials


class DownloadChecks(unittest.TestCase):
    def test_manual_credentials_do_not_enter_index(self):
        text = 'Camera rtsp://operator:private-password@192.0.2.8:554/stream?token=private-token\npassword = private-password'
        clean = scrub_credentials(text)
        self.assertNotIn('private-password', clean)
        self.assertNotIn('private-token', clean)
        self.assertIn('rtsp://192.0.2.8:554/stream', clean)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'README.md').write_text(text)
            with patch('corpus_cpu.subprocess.check_output', return_value='source-commit'):
                records, sources, fingerprint = collect_manuals(tmp, words=20, overlap=5)
                records2, _, fingerprint2 = collect_manuals(tmp, words=20, overlap=5)
            self.assertEqual(fingerprint, fingerprint2)
            self.assertEqual(records, records2)
            self.assertNotIn('private-password', json.dumps(records))

    def test_corruption_with_same_byte_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'model.safetensors'
            path.write_bytes(b'good')
            manifest = {'weight_bytes': 4, 'files': [{'path': path.name, 'bytes': 4,
                        'sha256': hashlib.sha256(b'good').hexdigest()}]}
            self.assertEqual(verify_files(Path(tmp), manifest)[0]['bytes'], 4)
            path.write_bytes(b'evil')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                verify_files(Path(tmp), manifest)

    def test_partial_download_and_wrong_total_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {'weight_bytes': 8, 'files': [{'path': 'model.safetensors', 'bytes': 4}]}
            with self.assertRaisesRegex(ValueError, 'Missing or wrong-sized'):
                verify_files(root, manifest)
            (root / 'model.safetensors').write_bytes(b'abcd')
            with self.assertRaisesRegex(ValueError, 'Total weight'):
                verify_files(root, manifest)


if __name__ == '__main__': unittest.main()
