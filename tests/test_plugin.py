import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import Mock, patch

from PIL import Image
from flask import Flask
import support


class PluginTests(unittest.TestCase):
    def setUp(self):
        base = types.ModuleType('plugins.base_plugin.base_plugin')
        class Base:
            def __init__(self, config):
                self.config = config
        base.BasePlugin = Base
        folder = Path(__file__).resolve().parents[1] / 'plugins/game_display'
        package = types.ModuleType('tested_game_plugin')
        package.__path__ = [str(folder)]
        with patch.dict(sys.modules, {'plugins.base_plugin.base_plugin': base,
                                     'tested_game_plugin': package}):
            spec = importlib.util.spec_from_file_location('tested_game_plugin.game_display', folder/'game_display.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.plugin = module.GameDisplayPlugin({'id': 'game_display'})
        self.temp = tempfile.TemporaryDirectory()
        self.plugin.source.config_path = Path(self.temp.name)/'config.json'
        self.plugin.controls.path = Path(self.temp.name)/'controls.json'
        self.plugin.settings.path = self.plugin.source.config_path
        self.plugin.load_token = Mock(return_value='test-native-token')
        self.config = Mock(current_image_file=str(Path(self.temp.name)/'current.png'))
        self.config.get_resolution.return_value = (800, 480)
        self.previous = Image.new('RGB', (800, 480), 'white')
        self.previous.save(self.config.current_image_file)
        self.plugin.task = Mock(device_config=self.config)
        self.plugin.original_select = Mock(return_value=('Evening', 'evening-plugin'))
        self.latest = types.SimpleNamespace(plugin_id='clock', image_hash='old', refresh_time='recent')
        self.frame = Image.new('RGB', (800, 480), 'red')
        self.hash = module.compute_image_hash

    def tearDown(self):
        self.temp.cleanup()

    def enter(self):
        self.plugin.source.poll = Mock(return_value=self.frame)
        self.assertEqual(self.plugin.select(None, self.latest, None),
                         (self.plugin.playlist, self.plugin.instance))
        self.latest.plugin_id = 'game_display'
        self.latest.image_hash = self.hash(self.frame)

    def test_active_suppresses_schedule_and_unchanged_refreshes(self):
        self.enter()
        self.assertEqual(self.plugin.select(None, self.latest, None), (None, None))
        self.plugin.original_select.assert_not_called()

    def test_release_forces_current_schedule_then_clears_marker_after_success(self):
        self.enter()
        self.plugin.source.poll.return_value = None
        self.assertEqual(self.plugin.select(None, self.latest, None), ('Evening', 'evening-plugin'))
        due = self.plugin.original_select.call_args.args[1]
        self.assertIsNone(due.refresh_time)
        self.assertEqual(self.latest.refresh_time, 'recent')
        self.assertTrue(self.plugin.source.pending_resume())
        self.latest.plugin_id = 'weather'
        self.plugin.select(None, self.latest, None)
        self.assertFalse(self.plugin.source.pending_resume())

    def test_no_current_schedule_restores_previous_frame(self):
        self.enter()
        self.plugin.source.poll.return_value = None
        self.plugin.original_select.return_value = (None, None)
        self.plugin.select(None, self.latest, None)
        self.assertEqual(self.hash(self.plugin.frame), self.hash(self.previous))
        self.latest.image_hash = self.hash(self.previous)
        self.plugin.select(None, self.latest, None)
        self.assertFalse(self.plugin.source.pending_resume())

    def test_failed_resume_keeps_retry_marker(self):
        self.enter()
        self.plugin.source.poll.return_value = None
        self.plugin.select(None, self.latest, None)
        self.plugin.select(None, self.latest, None)
        self.assertTrue(self.plugin.source.pending_resume())
        self.assertEqual(self.plugin.original_select.call_count, 2)

    def test_disabling_during_game_resumes_playlist_without_polling(self):
        self.enter()
        data = self.plugin.controls.defaults()
        data['enabled'] = False
        self.plugin.controls.write(data)
        self.plugin.source.poll.reset_mock()
        self.assertEqual(self.plugin.select(None, self.latest, None), ('Evening', 'evening-plugin'))
        self.plugin.source.poll.assert_not_called()
        self.assertIsNone(self.plugin.source.identity)

    def test_schedule_boundary_releases_then_reenters(self):
        self.enter()
        data = self.plugin.controls.defaults()
        data['schedule_enabled'] = True
        data['hours'][0][20] = False
        self.plugin.controls.write(data)
        closed = datetime(2026, 11, 9, 20, 0, tzinfo=ZoneInfo('Australia/Sydney'))
        self.assertEqual(self.plugin.select(None, self.latest, closed), ('Evening', 'evening-plugin'))
        self.latest.plugin_id = 'clock'
        self.latest.image_hash = self.hash(self.previous)
        self.plugin.select(None, self.latest, closed)
        self.assertFalse(self.plugin.source.pending_resume())
        opened = closed.replace(hour=21)
        self.assertEqual(self.plugin.select(None, self.latest, opened),
                         (self.plugin.playlist, self.plugin.instance))

    def test_http_controls_persist_and_do_not_expose_credentials(self):
        app = Flask(__name__)
        app.config['REFRESH_TASK'] = self.plugin.task
        self.config.get_config.return_value = 'Australia/Sydney'
        with patch('threading.Thread.start'):
            app.register_blueprint(self.plugin.get_blueprint())
        client = app.test_client()
        response = client.get('/game_display/controls')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {'controls', 'timezone', 'allowed_now'})
        data = response.json['controls']
        data['enabled'] = False
        response = client.put('/game_display/controls', json=data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.plugin.controls.read()['enabled'])
        self.plugin.task.signal_config_change.assert_called_once()
        self.assertEqual(client.put('/game_display/controls', json=data,
                         headers={'Origin': 'https://other.example'}).status_code, 403)
        self.assertEqual(client.put('/game_display/controls', json={'enabled': False}).status_code, 400)

    def test_settings_api_and_connection_test(self):
        app = Flask(__name__)
        app.config['REFRESH_TASK'] = self.plugin.task
        self.config.get_config.return_value = 'UTC'
        with patch('threading.Thread.start'):
            app.register_blueprint(self.plugin.get_blueprint())
        client = app.test_client()
        self.assertEqual(client.get('/game_display/settings').status_code, 200)
        response = client.put('/game_display/settings', json={
            'ha_url': 'http://ha.test', 'master_entity': 'sensor.player'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['token_configured'])
        self.assertNotIn('test-native-token', response.get_data(as_text=True))
        self.assertEqual(client.put('/game_display/settings', json={'token': 'secret'}).status_code, 400)
        session = Mock()
        response = session.get.return_value
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {'state': 'A game'}
        with patch('requests.Session') as cls:
            cls.return_value.__enter__.return_value = session
            tested = client.post('/game_display/test_connection')
        self.assertEqual(tested.status_code, 200)
        self.assertTrue(tested.json['success'])
        self.assertNotIn('test-native-token', tested.get_data(as_text=True))
        self.assertEqual(session.get.call_args.kwargs['headers']['Authorization'], 'Bearer test-native-token')

    def test_native_api_key_loader_and_deleted_key(self):
        env = Path(self.temp.name)/'.env'
        env.write_text('HOME_ASSISTANT_TOKEN=saved-token\n')
        self.config.load_env_key.return_value = 'saved-token'
        with patch('blueprints.apikeys.get_env_path', return_value=str(env)):
            self.assertEqual(type(self.plugin).load_token(self.plugin), 'saved-token')
            env.write_text('')
            self.assertIsNone(type(self.plugin).load_token(self.plugin))
        self.config.load_env_key.assert_called_once_with('HOME_ASSISTANT_TOKEN')


if __name__ == '__main__':
    unittest.main()
