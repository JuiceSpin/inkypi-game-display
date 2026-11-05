import importlib.util
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('controls', Path(__file__).resolve().parents[1]/'plugins/game_display/controls.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Controls = module.Controls


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.controls = Controls(Path(self.tmp.name)/'controls.json')

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_unrestricted_and_master_switch_wins(self):
        now = datetime(2026, 11, 6, 0, 0)
        self.assertTrue(self.controls.allows(now))
        data = self.controls.defaults()
        data['enabled'] = False
        self.controls.write(data)
        self.assertFalse(self.controls.allows(now))
        self.assertFalse(Controls(self.controls.path).allows(now))
        self.assertEqual(self.controls.path.stat().st_mode & 0o777, 0o600)

    def test_hour_and_week_boundary(self):
        data = self.controls.defaults()
        data['schedule_enabled'] = True
        data['hours'] = [[False]*24 for _ in range(7)]
        data['hours'][6][23] = True
        self.controls.write(data)
        sunday = datetime(2026, 11, 8, 23, 59, tzinfo=ZoneInfo('Australia/Sydney'))
        monday = datetime(2026, 11, 9, 0, 0, tzinfo=ZoneInfo('Australia/Sydney'))
        self.assertTrue(self.controls.allows(sunday))
        self.assertFalse(self.controls.allows(monday))
        self.assertFalse(self.controls.allows(sunday.replace(hour=22)))

    def test_malformed_writes_preserve_saved_values(self):
        data = self.controls.defaults()
        self.controls.write(data)
        for bad in [None, {}, {**data, 'enabled': 'false'}, {**data, 'hours': []},
                    {**data, 'hours': [[1]*24 for _ in range(7)]}]:
            with self.assertRaises(ValueError):
                self.controls.write(bad)
            self.assertEqual(self.controls.read(), data)
