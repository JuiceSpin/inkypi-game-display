# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Portable, non-secret settings for Game Display."""
import re
from pathlib import Path
from urllib.parse import urlsplit
from .controls import Controls

TOKEN_KEY = 'HOME_ASSISTANT_TOKEN'
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'game_display' / 'settings.json'

# This schema also supplies labels, ranges and defaults to the settings UI.
FIELDS = [
    ('ha_url', 'Home Assistant URL', 'connection', 'url', '', None),
    ('master_entity', 'Gaming Status master sensor', 'connection', 'entity', '', 'sensor'),
    ('xbox_game_entity', 'Xbox now-playing sensor', 'entities', 'entity', '', 'sensor'),
    ('xbox_art_entity', 'Xbox titled hero artwork', 'entities', 'entity', '', 'image'),
    ('gsa_entity', 'PC agent sensor', 'entities', 'entity', '', 'sensor'),
    ('steam_entity', 'Steam presence sensor', 'entities', 'entity', '', 'sensor'),
    ('xbox_activity_entity', 'Xbox in-game sensor', 'entities', 'entity', '', 'binary_sensor'),
    ('poll_interval_seconds', 'Check for game changes (seconds)', 'timing', 'number', 15, (5, 300)),
    ('fast_stop_enabled', 'Use raw sensors for faster session end detection', 'timing', 'checkbox', True, None),
    ('stop_delay_seconds', 'Confirm all raw sources stopped (seconds)', 'timing', 'number', 30, (0, 600)),
    ('source_timeout_seconds', 'Release display after connection loss (seconds)', 'timing', 'number', 180, (15, 3600)),
    ('art_refresh_seconds', 'Recheck artwork (seconds)', 'timing', 'number', 300, (30, 3600)),
    ('request_timeout_seconds', 'Network request timeout (seconds)', 'timing', 'number', 8, (2, 60)),
    ('prefer_xbox_art', 'Prefer Xbox titled hero artwork', 'artwork', 'checkbox', True, None),
    ('retain_xbox_art', 'Keep preferred Xbox artwork for the session', 'artwork', 'checkbox', True, None),
    ('show_logo', 'Overlay the game logo when available', 'artwork', 'checkbox', True, None),
    ('show_title', 'Show the game title when no logo is available', 'artwork', 'checkbox', True, None),
    ('image_fit', 'Artwork sizing', 'artwork', 'select', 'contain', [('contain', 'Fit whole image'), ('cover', 'Fill screen (crop edges)')]),
    ('resume_mode', 'When an interruption ends', 'artwork', 'select', 'current_schedule', [('current_schedule', 'Resume current scheduled playlist'), ('previous_image', 'Restore previous image')]),
    ('background_color', 'Background colour', 'layout', 'color', '#101010', None),
    ('text_color', 'Title colour', 'layout', 'color', '#ffffff', None),
    ('font_size', 'Title font size', 'layout', 'number', 30, (12, 96)),
    ('padding', 'Logo / title padding (pixels)', 'layout', 'number', 32, (0, 150)),
    ('logo_width_percent', 'Maximum logo width (% of screen)', 'layout', 'number', 55, (10, 90)),
    ('logo_height_percent', 'Maximum logo height (% of screen)', 'layout', 'number', 28, (5, 60)),
    ('logo_position', 'Logo position', 'layout', 'select', 'bottom_left', [(x, x.replace('_', ' ').title()) for x in ['bottom_left', 'bottom_right', 'top_left', 'top_right', 'center']]),
    ('game_attribute', 'Game title attribute', 'attributes', 'attribute', 'current_game', None),
    ('platform_attribute', 'Platform attribute', 'attributes', 'attribute', 'active_platform_key', None),
    ('hero_attribute', 'Hero artwork attribute', 'attributes', 'attribute', 'game_hero_art', None),
    ('logo_attribute', 'Logo artwork attribute', 'attributes', 'attribute', 'game_logo_art', None),
    ('cover_attribute', 'Cover artwork fallback attribute', 'attributes', 'attribute', 'game_cover_art', None),
]


class Settings(Controls):
    @staticmethod
    def defaults():
        return {key: default for key, label, group, kind, default, limits in FIELDS}

    @staticmethod
    def schema():
        return [dict(key=key, label=label, group=group, kind=kind, default=default, limits=limits)
                for key, label, group, kind, default, limits in FIELDS]

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or set(data) - set(Settings.defaults()):
            raise ValueError('Unknown plugin setting; credentials belong in InkyPi API Keys')
        result = Settings.defaults()
        result.update(data)
        for key, label, group, kind, default, limits in FIELDS:
            value = result[key]
            if kind == 'checkbox':
                if type(value) is not bool:
                    raise ValueError(f'{label} must be on or off')
            elif kind == 'number':
                if type(value) is not int or not limits[0] <= value <= limits[1]:
                    raise ValueError(f'{label} must be between {limits[0]} and {limits[1]}')
            elif not isinstance(value, str):
                raise ValueError(f'{label} must be text')
            else:
                value = value.strip()
                result[key] = value
                if kind == 'url' and value:
                    try:
                        parsed = urlsplit(value)
                        port = parsed.port
                    except ValueError:
                        raise ValueError('Enter a valid Home Assistant URL') from None
                    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or
                            parsed.username or parsed.password or parsed.query or parsed.fragment):
                        raise ValueError('Use an http(s) Home Assistant URL without credentials, query or fragment')
                    result[key] = value.rstrip('/')
                elif kind == 'entity' and value and not re.fullmatch(re.escape(limits) + r'\.[a-z0-9_]+', value):
                    raise ValueError(f'{label} must be a {limits} entity ID')
                elif kind == 'color' and not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                    raise ValueError(f'{label} must be a six-digit hex colour')
                elif kind == 'select' and value not in {item[0] for item in limits}:
                    raise ValueError(f'Choose a valid {label.lower()}')
                elif kind == 'attribute' and value and not re.fullmatch(r'[A-Za-z0-9_ ]{1,80}', value):
                    raise ValueError(f'{label} contains unsupported characters')
        return result
