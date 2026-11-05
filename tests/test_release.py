import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('release_builder',Path(__file__).resolve().parents[1]/'scripts/build_release.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class ReleaseTests(unittest.TestCase):
    def test_archives_are_reproducible_and_source_complete(self):
        with tempfile.TemporaryDirectory() as first,tempfile.TemporaryDirectory() as second:
            one=builder.build(first);two=builder.build(second)
            self.assertEqual([p.read_bytes() for p in one],[p.read_bytes() for p in two])
            with zipfile.ZipFile(one[0]) as archive:
                names=archive.namelist()
                for required in ['LICENSE','NOTICE','README.md','scripts/install.py','docs/OPTIONS.md','plugins/game_display/artwork.py','tests/test_game_display.py']:
                    self.assertIn('inkypi-game-display-0.1.0/'+required,names)
                self.assertFalse(any('/__pycache__/' in name or name.endswith('/.env') or name.endswith('/settings.json') or name.endswith('/ha-token') for name in names))
                self.assertTrue(all(not name.startswith('/') and '..' not in Path(name).parts for name in names))
