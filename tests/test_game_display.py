import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from PIL import Image
from game_display.artwork import GameDisplay
from game_display.settings import Settings


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        config = root / 'config.json'
        config.write_text(json.dumps(dict(ha_url='http://ha.test',
                                         master_entity='sensor.master', xbox_game_entity='sensor.xbox_game',
                                         xbox_art_entity='image.xbox_art')))
        self.now = 1000
        self.game = GameDisplay(config, clock=lambda: self.now, token_loader=lambda: 'test-token')
        self.game._image = Mock(return_value=Image.new('RGBA', (1600, 900), 'red'))
        self.master = dict(state='A game', attributes=dict(current_game='A game',
                           active_platform_key='gsa', game_hero_art='/hero', game_logo_art='/logo'))
        self.states = {'sensor.master': self.master}
        self.game._state = lambda base, token, entity: self.states[entity]

    def tearDown(self):
        self.temp.cleanup()

    def test_pc_hero_logo_and_no_duplicate_download(self):
        first = self.game.poll((800, 480))
        self.assertEqual(first.size, (800, 480))
        self.assertEqual(self.game._image.call_count, 2)
        self.assertIs(self.game.poll((800, 480)), first)
        self.assertEqual(self.game._image.call_count, 2)

    def test_idle_releases_even_with_retained_art(self):
        self.game.poll((800, 480))
        self.master['state'] = 'Offline'
        self.assertIsNone(self.game.poll((800, 480)))
        self.assertFalse(self.game.active)

    def test_xbox_uses_titled_art(self):
        self.master['attributes']['active_platform_key'] = 'xbox'
        self.states.update({'sensor.xbox_game': {'state': 'A game'},
                           'image.xbox_art': {'state': 'timestamp', 'attributes': {'entity_picture': '/xbox-titled'}}})
        self.game.poll((800, 480))
        self.game._image.assert_called_once_with('http://ha.test', 'test-token', '/xbox-titled')

    def test_stale_xbox_art_not_used_for_different_title(self):
        self.master['attributes']['active_platform_key'] = 'xbox'
        self.states['sensor.xbox_game'] = {'state': 'Previous game'}
        self.game.poll((800, 480))
        self.assertEqual(self.game._image.call_args_list[0].args[2], '/hero')

    def test_lost_source_expires_override(self):
        frame = self.game.poll((800, 480))
        self.game._state = Mock(side_effect=ConnectionError)
        self.now += 60
        self.assertIs(self.game.poll((800, 480)), frame)
        self.now += 121
        self.assertIsNone(self.game.poll((800, 480)))

    def test_game_switch_with_failed_art_uses_new_title(self):
        first = self.game.poll((800, 480))
        self.master['state'] = self.master['attributes']['current_game'] = 'Another game'
        self.game._image.side_effect = ConnectionError
        second = self.game.poll((800, 480))
        self.assertIsNot(first, second)
        self.assertEqual(self.game.identity[0], 'Another game')

    def test_unknown_is_treated_as_connection_loss(self):
        frame = self.game.poll((800, 480))
        self.master['state'] = 'unavailable'
        self.assertIs(self.game.poll((800, 480)), frame)
        self.now += 181
        self.assertIsNone(self.game.poll((800, 480)))

    def test_restart_preserves_need_to_resume_and_previous_image(self):
        previous = Image.new('RGB', (800, 480), 'blue')
        self.game.begin_override(previous)
        restarted = GameDisplay(self.game.config_path)
        self.assertTrue(restarted.pending_resume())
        self.assertEqual(restarted.previous_image().getpixel((0, 0)), (0, 0, 255))
        restarted.finish_resume()
        self.assertFalse(restarted.pending_resume())

    def test_preferred_xbox_art_pinned_when_live_title_clears(self):
        self.master['attributes']['active_platform_key'] = 'xbox'
        self.states.update({'sensor.xbox_game': {'state': 'A game'},
                           'image.xbox_art': {'state': 'timestamp', 'attributes': {'entity_picture': '/titled'}}})
        first = self.game.poll((800, 480))
        self.states['sensor.xbox_game']['state'] = 'unknown'
        self.now += 301
        self.assertIs(self.game.poll((800, 480)), first)
        self.assertEqual(self.game._image.call_count, 1)

    def configure_activity(self):
        config = json.loads(self.game.config_path.read_text())
        config.update(gsa_entity='sensor.raw_pc', steam_entity='sensor.raw_steam', xbox_activity_entity='binary_sensor.raw_xbox')
        config['stop_delay_seconds'] = 30
        self.game.config_path.write_text(json.dumps(config))
        self.states.update({'sensor.raw_pc': {'state': 'Offline'},
                           'sensor.raw_steam': {'state': 'online', 'attributes': {'game': None}},
                           'binary_sensor.raw_xbox': {'state': 'off'}})

    def test_raw_idle_releases_before_master_grace_and_stays_released(self):
        self.configure_activity()
        self.assertIsNotNone(self.game.poll((800, 480)))
        self.now += 29
        self.assertIsNotNone(self.game.poll((800, 480)))
        self.now += 1
        self.assertIsNone(self.game.poll((800, 480)))
        self.now += 15
        self.assertIsNone(self.game.poll((800, 480)))
        self.states['binary_sensor.raw_xbox']['state'] = 'on'
        self.assertIsNotNone(self.game.poll((800, 480)))

    def test_unknown_activity_does_not_prematurely_release(self):
        self.configure_activity()
        self.game.poll((800, 480))
        self.states['binary_sensor.raw_xbox']['state'] = 'unavailable'
        self.now += 31
        self.assertIsNotNone(self.game.poll((800, 480)))

    def test_any_raw_game_prevents_early_release(self):
        self.configure_activity()
        self.states['sensor.raw_steam']['attributes']['game'] = 'A game'
        self.game.poll((800, 480))
        self.now += 100
        self.assertIsNotNone(self.game.poll((800, 480)))

    def set_options(self, **options):
        data = json.loads(self.game.config_path.read_text())
        data.update(options)
        self.game.config_path.write_text(json.dumps(data))

    def test_native_token_required_and_deletion_releases(self):
        self.assertIsNotNone(self.game.poll((800, 480)))
        self.game.token_loader = lambda: None
        self.assertIsNone(self.game.poll((800, 480)))

    def test_layout_and_logo_can_be_configured(self):
        self.set_options(show_logo=False, show_title=False, image_fit='cover')
        frame = self.game.poll((800, 480))
        self.assertEqual(frame.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(self.game._image.call_count, 1)

    def test_attribute_names_and_source_timeout_configurable(self):
        self.set_options(game_attribute='game', hero_attribute='hero', source_timeout_seconds=20)
        self.master['attributes'].update(game='Renamed game', hero='/new-hero')
        self.assertIsNotNone(self.game.poll((800, 480)))
        self.assertEqual(self.game.identity[0], 'Renamed game')
        self.assertEqual(self.game._image.call_args_list[0].args[2], '/new-hero')
        self.game._state = Mock(side_effect=ConnectionError)
        self.now += 21
        self.assertIsNone(self.game.poll((800, 480)))


if __name__ == '__main__':
    unittest.main()
