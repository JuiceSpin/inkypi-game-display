# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Temporary game artwork override; called only by InkyPi's refresh worker."""
import io
import logging
import time
from pathlib import Path
from .settings import Settings, DEFAULT_CONFIG
from urllib.parse import urljoin, urlsplit

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

LOG = logging.getLogger(__name__)
CONFIG = DEFAULT_CONFIG
IDLE = {'offline', 'online', 'idle', 'unknown', 'unavailable', 'none', ''}


class GameDisplay:
    def __init__(self, config_path=CONFIG, clock=time.monotonic, token_loader=None):
        self.config_path = Path(config_path)
        self.clock = clock
        self.session = requests.Session()
        self.token_loader = token_loader or (lambda: "")
        self.options = Settings.defaults()
        self.last_good = None
        self.frame = None
        self.identity = None
        self.art_key = None
        self.last_art_check = -1000
        self.active = False
        self.error_logged = False
        self.raw_idle_since = None

    def raw_sources_idle(self, config, base, token):
        sources = {kind: config[key] for kind, key in [('gsa', 'gsa_entity'), ('steam', 'steam_entity'), ('xbox', 'xbox_activity_entity')] if config.get(key)}
        if not config['fast_stop_enabled']:
            return False
        if not sources:
            return False
        for kind, entity in sources.items():
            try:
                state = self._state(base, token, entity)
            except requests.RequestException:
                return False  # Fall back to the master if a raw source is unavailable.
            value = str(state.get('state', '')).strip().lower()
            if value in {'unknown', 'unavailable', ''}:
                return False  # Missing data cannot confirm a stopped session.
            if kind == 'steam':
                if state.get('attributes', {}).get('game'):
                    return False
            elif kind == 'xbox':
                if value != 'off':
                    return False
            elif kind == 'gsa':
                if value not in IDLE:
                    return False
            else:
                return False
        return True

    def _state(self, base, token, entity):
        response = self.session.get(
            base + '/api/states/' + entity,
            headers={'Authorization': 'Bearer ' + token}, timeout=(3, self.options['request_timeout_seconds']), allow_redirects=False)
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("Home Assistant redirects are not supported; use the direct base URL")
        return response.json()

    def _image(self, base, token, path):
        url = urljoin(base + '/', path)
        if urlsplit(url).netloc != urlsplit(base).netloc:
            raise ValueError('Artwork must be served by Home Assistant')
        with self.session.get(url, headers={'Authorization': 'Bearer ' + token},
                              timeout=(3, self.options["request_timeout_seconds"]), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError('Artwork redirect refused')
            data = bytearray()
            for block in response.iter_content(65536):
                data.extend(block)
                if len(data) > 12 * 1024 * 1024:
                    raise ValueError('Artwork exceeds size limit')
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError('Artwork dimensions exceed limit')
            return image.convert('RGBA')

    def pending_resume(self):
        return self.config_path.with_name('override-active').exists()

    def previous_image(self):
        try:
            with Image.open(self.config_path.with_name('previous.png')) as image:
                return image.copy()
        except (OSError, ValueError):
            return None

    def begin_override(self, previous):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        if previous is not None:
            previous.save(self.config_path.with_name('previous.png'))
        self.config_path.with_name('override-active').touch(mode=0o600)

    def finish_resume(self):
        self.config_path.with_name('override-active').unlink(missing_ok=True)
        self.config_path.with_name('previous.png').unlink(missing_ok=True)

    @staticmethod
    def render(hero, logo, title, size, options=None):
        # Contain artwork: preserve titles near the edges rather than cropping.
        options = options or Settings.defaults()
        padding = min(options['padding'], max(0, min(size) // 4))
        frame = Image.new('RGB', size, options['background_color'])
        if hero is not None:
            resize = ImageOps.fit if options['image_fit'] == 'cover' else ImageOps.contain
            fitted = resize(hero.convert('RGB'), size)
            frame.paste(fitted, ((size[0] - fitted.width) // 2,
                                 (size[1] - fitted.height) // 2))
        if logo is not None and options['show_logo']:
            fitted = ImageOps.contain(logo, (max(1, min(size[0]-2*padding, int(size[0]*options['logo_width_percent']/100))), max(1, min(size[1]-2*padding, int(size[1]*options['logo_height_percent']/100)))))
            position = options['logo_position']
            x = padding if position.endswith('left') else size[0]-fitted.width-padding
            y = padding if position.startswith('top') else size[1]-fitted.height-padding
            if position == 'center':
                x, y = (size[0]-fitted.width)//2, (size[1]-fitted.height)//2
            frame.paste(fitted, (x, y), fitted)
        elif title and options['show_title']:
            draw = ImageDraw.Draw(frame)
            try:
                font = ImageFont.truetype('DejaVuSans.ttf', options['font_size'])
            except OSError:
                font = ImageFont.load_default()
            words, lines, line = title.split(), [], ''
            for word in words:
                candidate = (line + ' ' + word).strip()
                if draw.textlength(candidate, font=font) > size[0] - 2*padding and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
            lines = lines[:3]
            height = min(size[1], len(lines) * (options['font_size']+8) + 24)
            draw.rectangle((0, size[1] - height, size[0], size[1]), fill=options['background_color'])
            draw.multiline_text((padding, size[1] - height + 12), '\n'.join(lines),
                                font=font, fill=options['text_color'], spacing=4)
        return frame

    def poll(self, size):
        """Return an override image, or None to allow the normal scheduler."""
        if not self.config_path.exists():
            return None
        try:
            config = Settings(self.config_path).read()
            if config != self.options:
                self.identity = self.art_key = None
                self.raw_idle_since = None
                self.options = config
            base = config['ha_url'].rstrip('/')
            token = (self.token_loader() or '').strip()
            if not base or not config['master_entity'] or not token:
                self.active = False
                self.frame = None
                self.identity = self.art_key = None
                return None
            state = self._state(base, token, config['master_entity'])
            value = str(state.get('state', '')).strip()
            if value.lower() in {'unknown', 'unavailable'}:
                raise ValueError('Game status unavailable')
            self.last_good = self.clock()
            self.error_logged = False
            attrs = state.get('attributes', {})
            if self.raw_sources_idle(config, base, token):
                if self.raw_idle_since is None:
                    self.raw_idle_since = self.clock()
            else:
                self.raw_idle_since = None
            raw_stopped = (self.raw_idle_since is not None and
                           self.clock() - self.raw_idle_since >= config.get('stop_delay_seconds', 30))
            if value.lower() in IDLE or raw_stopped:
                self.active = False
                self.frame = None
                self.identity = self.art_key = None
                return None
            title = attrs.get(config['game_attribute']) or value
            platform = attrs.get(config['platform_attribute'], '')
            identity = (title, platform)
            changed = identity != self.identity
            if changed:
                self.identity = identity
                self.art_key = None
                self.frame = self.render(None, None, title, size, config)
            self.active = True

            # Once preferred Xbox artwork is acquired, pin it for this identity.
            # A grace-period title mismatch or expiring proxy must not downgrade it.
            if platform == 'xbox' and config['retain_xbox_art'] and self.art_key and self.art_key[2]:
                return self.frame

            # Retry missing/late art; also follow token or art attribute changes.
            hero = attrs.get(config['hero_attribute']) or attrs.get(config['cover_attribute'])
            logo = attrs.get(config['logo_attribute']) if config['show_logo'] else None
            titled = False
            if platform == 'xbox' and config['prefer_xbox_art'] and config['xbox_game_entity'] and config['xbox_art_entity']:
                # Only use Xbox art when its live title matches the master.
                now = self._state(base, token, config['xbox_game_entity'])
                if now.get('state') == title:
                    art = self._state(base, token, config['xbox_art_entity'])
                    if art.get('state') not in {'unknown', 'unavailable'}:
                        hero = art.get('attributes', {}).get('entity_picture') or hero
                        titled = bool(art.get('attributes', {}).get('entity_picture'))
                        if titled:
                            logo = None
            art_key = (hero, logo, titled)
            if changed or art_key != self.art_key or self.clock() - self.last_art_check > config['art_refresh_seconds']:
                self.last_art_check = self.clock()
                if hero:
                    hero_image = self._image(base, token, hero)
                    logo_image = None
                    if logo:
                        try:
                            logo_image = self._image(base, token, logo)
                        except Exception:
                            LOG.warning('Game logo unavailable; using text title')
                    self.frame = self.render(hero_image, logo_image,
                                             '' if titled else title, size, config)
                    self.art_key = art_key
            return self.frame
        except Exception as error:
            # Never log URLs/tokens from HTTP errors.
            if not self.error_logged:
                LOG.warning('Game display source unavailable (%s)', type(error).__name__)
                self.error_logged = True
            if self.active and self.last_good is not None:
                # Artwork failure should retain the current title fallback.
                if self.clock() - self.last_good < self.options['source_timeout_seconds']:
                    return self.frame
            self.active = False
            self.frame = None
            self.identity = self.art_key = None
            return None
