import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('snapshot', Path(__file__).resolve().parents[1] / 'deploy/publication/snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class SnapshotTest(unittest.TestCase):
    def test_rejects_traversal_and_links(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('editions/link', tarfile.SYMTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with tarfile.open(root / 'site.tar.gz', 'w:gz') as archive:
                    item = tarfile.TarInfo(name)
                    item.type = kind
                    item.linkname = '../escape' if kind == tarfile.SYMTYPE else ''
                    archive.addfile(item, io.BytesIO(b''))
                with self.assertRaises(ValueError):
                    snapshot.extract(root / 'site.tar.gz', root / 'out')

    def test_keeps_old_editions_and_rejects_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'old/editions/one').mkdir(parents=True)
            (root / 'old/editions/one/manifest.json').write_text('{}')
            snapshot.merge(root / 'old', root / 'site')
            self.assertEqual((root / 'site/editions/one/manifest.json').read_text(), '{}')
            with self.assertRaises(ValueError):
                snapshot.merge(root / 'old', root / 'site')
