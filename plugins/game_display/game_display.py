# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Automatic game override using InkyPi's installed plugin blueprint extension."""
import copy
import logging
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from PIL import Image
from plugins.base_plugin.base_plugin import BasePlugin
from utils.image_utils import compute_image_hash
from .artwork import GameDisplay
from .controls import Controls
from .settings import Settings, TOKEN_KEY

LOG = logging.getLogger(__name__)


class GameDisplayPlugin(BasePlugin):
    def __init__(self, config):
        super().__init__(config)
        self.source = GameDisplay()
        self.source.token_loader = self.load_token
        self.settings = Settings(self.source.config_path)
        self.controls = Controls(self.source.config_path.with_name('controls.json'))
        self.frame = None
        self.restore_hash = None
        self.task = None
        self.wake_event = threading.Event()
        self.instance = SimpleNamespace(
            plugin_id='game_display', name='Automatic game display', settings={},
            get_image_path=lambda: 'automatic_game_display.png',
            should_refresh=lambda now: True, latest_refresh_time=None)
        self.playlist = SimpleNamespace(name='Game display override')

    def load_token(self):
        # Check the native store as well as loading it: deleted keys must not
        # survive in os.environ after removal through the API-key interface.
        from blueprints.apikeys import get_env_path
        from dotenv import dotenv_values
        if not self.task or TOKEN_KEY not in dotenv_values(get_env_path()):
            return None
        return self.task.device_config.load_env_key(TOKEN_KEY)

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params['api_key'] = {'required': True, 'service': 'Home Assistant',
                             'expected_key': TOKEN_KEY}
        return params

    def get_blueprint(self):
        bp = Blueprint('game_display', __name__)

        @bp.route('/game_display/settings', methods=['GET', 'PUT'])
        def settings():
            try:
                if request.method == 'PUT':
                    origin = request.headers.get('Origin')
                    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
                        return jsonify(error='Save settings from the InkyPi interface'), 403
                    if not request.is_json:
                        return jsonify(error='Expected JSON settings'), 415
                    data = self.settings.write(request.get_json())
                    self.wake_event.set()
                    self.task.signal_config_change()
                else:
                    data = self.settings.read()
                return jsonify(settings=data, fields=self.settings.schema(),
                               token_key=TOKEN_KEY, token_configured=bool(self.load_token()))
            except (ValueError, TypeError) as error:
                return jsonify(error=str(error)), 400
            except OSError:
                return jsonify(error='Could not save or load plugin settings'), 500

        @bp.route('/game_display/test_connection', methods=['POST'])
        def test_connection():
            # Read-only probe; do not mutate the running artwork session.
            import requests
            try:
                data = self.settings.read()
                token = self.load_token()
                if not data['ha_url'] or not data['master_entity'] or not token:
                    return jsonify(error='Set the Home Assistant URL, master sensor and API key first'), 400
                entities = [data[key] for key in ('master_entity', 'xbox_game_entity',
                            'xbox_art_entity', 'gsa_entity', 'steam_entity', 'xbox_activity_entity') if data[key]]
                results = []
                with requests.Session() as session:
                    for entity in dict.fromkeys(entities):
                        response = session.get(data['ha_url']+'/api/states/'+entity,
                            headers={'Authorization': 'Bearer '+token},
                            timeout=(3, data['request_timeout_seconds']), allow_redirects=False)
                        if response.status_code in (401, 403):
                            return jsonify(error='Home Assistant rejected the API key; check InkyPi API Keys'), 400
                        if response.is_redirect:
                            return jsonify(error='Use the direct Home Assistant base URL, without redirects'), 400
                        if response.status_code == 404:
                            results.append({'entity': entity, 'status': 'Not found'})
                        else:
                            response.raise_for_status()
                            results.append({'entity': entity, 'status': response.json().get('state', 'unknown')})
                return jsonify(results=results, success=all(x['status'] not in ('Not found', 'unavailable', 'unknown') for x in results))
            except (ValueError, OSError):
                return jsonify(error='Could not load plugin settings'), 400
            except requests.RequestException:
                return jsonify(error='Could not reach Home Assistant; check its URL and connection'), 400

        @bp.route('/game_display/controls', methods=['GET', 'PUT'])
        def controls():
            timezone = self.task.device_config.get_config('timezone', default='UTC')
            try:
                if request.method == 'PUT':
                    origin = request.headers.get('Origin')
                    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
                        return jsonify(error='Save settings from the InkyPi interface'), 403
                    if not request.is_json:
                        return jsonify(error='Expected JSON settings'), 415
                    data = self.controls.write(request.get_json())
                    self.task.signal_config_change()
                else:
                    data = self.controls.read()
                return jsonify(controls=data, timezone=timezone,
                               allowed_now=self.controls.allows(datetime.now(ZoneInfo(timezone))))
            except (ValueError, TypeError) as error:
                return jsonify(error=str(error)), 400
            except OSError:
                LOG.exception('Could not save or load Game Display controls')
                return jsonify(error='Could not save or load interruption settings'), 500

        @bp.record_once
        def attach(state):
            self.task = state.app.config['REFRESH_TASK']
            self.original_select = self.task._determine_next_plugin
            self.task._determine_next_plugin = self.select
            threading.Thread(target=self.wake, name='game-display-wake', daemon=True).start()
            LOG.info('Game Display plugin attached; normal schedules preserved')

        return bp

    def wake(self):
        while True:
            try:
                interval = self.settings.read()['poll_interval_seconds']
            except (ValueError, OSError):
                interval = 15
            self.wake_event.wait(interval)
            self.wake_event.clear()
            if self.task.running:
                self.task.signal_config_change()

    def select(self, manager, latest, now):
        # Called inside the existing worker's lock. It remains the sole writer.
        config = self.task.device_config
        try:
            allowed = self.controls.allows(now)
        except (ValueError, OSError):
            LOG.warning('Invalid Game Display controls; interruptions suspended')
            allowed = False
        if allowed:
            frame = self.source.poll(config.get_resolution())
        else:
            self.source.active = False
            self.source.frame = None
            self.source.identity = self.source.art_key = None
            self.source.raw_idle_since = None
            frame = None
        if frame is not None:
            if not self.source.pending_resume():
                try:
                    with Image.open(config.current_image_file) as previous:
                        self.source.begin_override(previous.copy())
                except OSError:
                    self.source.begin_override(None)
            self.frame = frame
            self.restore_hash = None
            if compute_image_hash(frame) == latest.image_hash:
                return None, None
            return self.playlist, self.instance

        if self.source.pending_resume():
            # A previous successful normal refresh completes the release.
            if latest.plugin_id != 'game_display' or (
                    self.restore_hash is not None and latest.image_hash == self.restore_hash):
                self.source.finish_resume()
                self.restore_hash = None
            else:
                due = copy.copy(latest)
                due.refresh_time = None
                try:
                    mode = self.settings.read()['resume_mode']
                except (ValueError, OSError):
                    mode = 'current_schedule'
                playlist, instance = ((None, None) if mode == 'previous_image' else
                                      self.original_select(manager, due, now))
                if instance:
                    return playlist, instance
                previous = self.source.previous_image()
                if previous is not None:
                    self.frame = previous
                    self.restore_hash = compute_image_hash(previous)
                    if self.restore_hash == latest.image_hash:
                        self.source.finish_resume()
                        return None, None
                    return self.playlist, self.instance
        return self.original_select(manager, latest, now)

    def generate_image(self, settings, device_config):
        if self.frame is None:
            raise RuntimeError('Game Display is automatic; launch a game to show artwork')
        return self.frame.copy()
