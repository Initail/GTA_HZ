import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'assets.py'
spec = importlib.util.spec_from_file_location('assets', MODULE)
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class ArchiveTests(unittest.TestCase):
    def test_rejects_traversal_and_absolute_paths(self):
        for value in ['../outside', '/absolute', 'a/../../outside', 'C:/outside', 'a\\b']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                assets.safe_path(value)

    def test_rejects_mismatch_without_installing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'assets.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('city.json', 'changed')
            manifest = {'files': {'city.json': {'bytes': 7, 'sha256': '0' * 64}}}
            with self.assertRaises(ValueError):
                assets.install_archive(archive, root / 'public', manifest)
            self.assertFalse((root / 'public').exists())

    def test_verifies_and_installs_exact_manifest_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'assets.zip'
            content = b'{"cityId":"hangzhou"}'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('city/data.json', content)
            manifest = {'files': {'city/data.json': {'bytes': len(content), 'sha256': assets.digest_bytes(content)}}}
            assets.install_archive(archive, root / 'public', manifest)
            assets.verify(root / 'public', manifest)
            (root / 'public/city/data.json').write_bytes(b'broken')
            with self.assertRaises(ValueError):
                assets.verify(root / 'public', manifest)


if __name__ == '__main__':
    unittest.main()
