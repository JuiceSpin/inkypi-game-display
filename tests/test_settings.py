from pathlib import Path
import tempfile
import unittest
from game_display.settings import Settings, DEFAULT_CONFIG


class SettingsTests(unittest.TestCase):
    def test_no_user_specific_defaults_or_credentials(self):
        data = Settings.defaults()
        self.assertEqual(data['ha_url'], '')
        self.assertEqual(data['master_entity'], '')
        self.assertEqual(DEFAULT_CONFIG.name, 'settings.json')
        self.assertNotIn('token_file', data)
        self.assertNotIn('token', data)

    def test_validation_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(Path(tmp)/'settings.json')
            data = settings.write({'ha_url': 'http://ha.test:8123/', 'master_entity': 'sensor.player'})
            self.assertEqual(data['ha_url'], 'http://ha.test:8123')
            self.assertEqual(settings.read(), data)
            self.assertEqual(data['poll_interval_seconds'], 15)
            for invalid in [
                {'token_file': '/tmp/token'}, {'HOME_ASSISTANT_TOKEN': 'secret'},
                {'ha_url': 'http://user:password@ha.test'}, {'ha_url': 'file:///tmp/foo'},
                {'master_entity': '../bad'}, {'poll_interval_seconds': 0},
                {'request_timeout_seconds': True}, {'text_color': 'red'},
                {'image_fit': 'invalid'}, {'show_logo': 'true'}]:
                with self.assertRaises(ValueError):
                    settings.write(invalid)
                self.assertEqual(settings.read(), data)

    def test_unused_platforms_can_be_blank(self):
        data = Settings.validate({'ha_url': 'https://ha.test', 'master_entity': 'sensor.player',
                                  'xbox_game_entity': '', 'gsa_entity': ''})
        self.assertEqual(data['xbox_game_entity'], '')
