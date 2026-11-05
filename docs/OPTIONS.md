# Complete options reference

Only the HA URL, player master sensor and native API key are required for initial setup. Leave everything else at its defaults until the first live test succeeds.

## Credential

In **InkyPi → API Keys**, add `HOME_ASSISTANT_TOKEN`. This is a Home Assistant long-lived access token, not an MQTT password or a SteamGridDB key. It is never saved in the ordinary plugin settings. The settings UI reports only Configured/Not configured.

## Interruption switch and schedule

| Control | Default | Behaviour |
| --- | --- | --- |
| Allow game interruptions | On | Global override. Off releases active game art and prevents new interruptions. |
| Use weekly schedule | Off | When off, selected cells do not restrict interruptions. When on, only selected hours are allowed. |
| Weekly hours | All 168 selected | Seven day rows × 24 hour columns. Each cell starts at its labelled hour. |
| Allow all / Clear all | — | Edit the grid; use Save schedule afterwards. |

Switches save immediately. Grid edits require **Save schedule**. The display follows InkyPi’s timezone, including daylight-saving transitions; the grid represents local wall-clock hours. Leaving an allowed hour releases the override and entering one may display an already-running game. A refresh already underway finishes first.

## Plugin settings

Expand **Connection & artwork settings**, edit fields, then choose **Save settings**. **Test saved connection** uses the saved values; save edits first. The tables below list all 31 options.

### Home Assistant connection

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Home Assistant URL<br>`ha_url` | Not set | HTTP(S) base URL | Required. Direct HA base address reachable from the Pi; no /api suffix, embedded login, query string or redirect. HTTP and HTTPS are supported; HTTPS certificates are verified. |
| Gaming Status master sensor<br>`master_entity` | Not set | `sensor.…` or blank | Required. Player master sensor from Gaming Status. Its state is the game title; do not select Anyone Gaming. |

### Optional platform entities

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Xbox now-playing sensor<br>`xbox_game_entity` | Not set | `sensor.…` or blank | Optional. Native Xbox sensor with the live game title. Set together with the Xbox artwork entity to match artwork to the game. |
| Xbox titled hero artwork<br>`xbox_art_entity` | Not set | `image.…` or blank | Optional. Native Xbox image entity for titled hero art. The plugin reads its entity_picture attribute. |
| PC agent sensor<br>`gsa_entity` | Not set | `sensor.…` or blank | Optional. Gaming Status Agent sensor on the gaming PC. Used only for faster session-end detection. |
| Steam presence sensor<br>`steam_entity` | Not set | `sensor.…` or blank | Optional. Native Steam presence sensor. A nonempty game attribute means a game is running; online without a game is idle. |
| Xbox in-game sensor<br>`xbox_activity_entity` | Not set | `binary_sensor.…` or blank | Optional. Native Xbox binary sensor that is on while playing. Used only for faster session-end detection. |

### Timing

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Check for game changes (seconds)<br>`poll_interval_seconds` | `15` | 5–300 | How often the existing refresh worker is asked to check game status. Does not force unchanged images to refresh. |
| Use raw sensors for faster session end detection<br>`fast_stop_enabled` | On | On / Off | Use the configured raw PC, Steam and Xbox sources to release the display before Gaming Status’s grace period expires. With no raw sources configured, use the master sensor. |
| Confirm all raw sources stopped (seconds)<br>`stop_delay_seconds` | `30` | 0–600 | All configured raw sources must continuously confirm no game for this long. Unavailable/unknown sources fall back to the master; polling and panel refresh add to visible delay. |
| Release display after connection loss (seconds)<br>`source_timeout_seconds` | `180` | 15–3600 | How long to retain an active game image after valid master status responses stop. Missing or removed credentials release the override rather than waiting for this timeout. |
| Recheck artwork (seconds)<br>`art_refresh_seconds` | `300` | 30–3600 | Recheck unpinned artwork after this interval. Changed artwork references and game changes can update earlier; missing artwork is retried on subsequent polls. |
| Network request timeout (seconds)<br>`request_timeout_seconds` | `8` | 2–60 | Read timeout for each HA request. Connection establishment has an additional fixed three-second limit; this is not a deadline for the entire multi-entity poll. |

### Artwork and return behaviour

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Prefer Xbox titled hero artwork<br>`prefer_xbox_art` | On | On / Off | Use the native titled Xbox hero image when the live Xbox game title matches the selected master game. Missing/mismatched art falls back to the master artwork. |
| Keep preferred Xbox artwork for the session<br>`retain_xbox_art` | On | On / Off | Once preferred Xbox art is acquired, retain it for the same game/platform identity so a grace-period title change or proxy update cannot downgrade it. |
| Overlay the game logo when available<br>`show_logo` | On | On / Off | Overlay the configured logo on PC or fallback artwork. Native titled Xbox artwork already contains a title and is not overlaid. |
| Show the game title when no logo is available<br>`show_title` | On | On / Off | Draw a text title when no logo is available or logos are disabled. Also supplies a missing-artwork title card; turning it off can leave only the configured background. |
| Artwork sizing<br>`image_fit` | `contain` | `contain` (Fit whole image), `cover` (Fill screen (crop edges)) | Fit whole image uses letterboxing and preserves edges. Fill screen crops edges to cover the panel and can crop titles embedded in artwork. |
| When an interruption ends<br>`resume_mode` | `current_schedule` | `current_schedule` (Resume current scheduled playlist), `previous_image` (Restore previous image) | Resume the playlist currently scheduled when the interruption ends, or restore the image captured before play. If no playlist is active, the previous image is used when available. Normal scheduling continues afterwards. |

### Layout

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Background colour<br>`background_color` | `#101010` | `#RRGGBB` | Colour behind letterboxed artwork and text title cards; also used for the title strip. |
| Title colour<br>`text_color` | `#ffffff` | `#RRGGBB` | Colour of the rendered text title. Does not recolour a logo or title embedded in source artwork. |
| Title font size<br>`font_size` | `30` | 12–96 | Requested text title font size in pixels; text wraps to at most three lines. Uses DejaVu Sans when available and a Pillow default font otherwise. |
| Logo / title padding (pixels)<br>`padding` | `32` | 0–150 | Insets the logo and text title. Clamped to a quarter of the shorter screen side on small displays to keep content within bounds. |
| Maximum logo width (% of screen)<br>`logo_width_percent` | `55` | 10–90 | Maximum logo width relative to the display; aspect ratio is preserved and padding can reduce the available space. |
| Maximum logo height (% of screen)<br>`logo_height_percent` | `28` | 5–60 | Maximum logo height relative to the display; both width and height limits apply. |
| Logo position<br>`logo_position` | `bottom_left` | `bottom_left` (Bottom Left), `bottom_right` (Bottom Right), `top_left` (Top Left), `top_right` (Top Right), `center` (Center) | Corner or centre placement for the overlaid logo. Does not move text fallback titles or baked-in artwork titles. |

### Advanced attribute mappings

| UI option / stored key | Default | Allowed values | Details |
| --- | --- | --- | --- |
| Game title attribute<br>`game_attribute` | `current_game` | Attribute name or blank | Master attribute holding the current game title. If absent or blank, use the sensor state. |
| Platform attribute<br>`platform_attribute` | `active_platform_key` | Attribute name or blank | Master attribute holding the platform key. The value xbox activates native Xbox artwork handling. |
| Hero artwork attribute<br>`hero_attribute` | `game_hero_art` | Attribute name or blank | Master attribute holding the hero image path. If absent, try the cover fallback. |
| Logo artwork attribute<br>`logo_attribute` | `game_logo_art` | Attribute name or blank | Master attribute holding the logo image path. Leave blank to skip a logo attribute. |
| Cover artwork fallback attribute<br>`cover_attribute` | `game_cover_art` | Attribute name or blank | Master attribute holding a cover image path, used when hero artwork is missing. Leave blank to disable this image fallback. |

## Inherited settings

Resolution, orientation, inversion, image enhancements and timezone come from InkyPi. Change them in InkyPi rather than maintaining duplicate plugin values. The game plugin does not change Gaming Status’s own grace periods or your future HA Game Mode automation.

## Persistence and API

Non-secret plugin preferences are in `src/config/game_display/settings.json`; interruption controls are in `controls.json`. Writes are atomic. Credentials remain in the native API-key store. Saving new preferences takes effect without restarting InkyPi.

The UI uses GET/PUT `/game_display/settings`, GET/PUT `/game_display/controls`, and POST `/game_display/test_connection`. PUT replaces the settings document and fills omitted plugin preferences with defaults; API callers should GET, edit and PUT the full document to preserve other preferences. These endpoints share the installed InkyPi web interface’s access controls; do not expose that interface as a public notification endpoint. General push notifications are outside this release.

## Source and artwork rules

Unknown or unavailable master status is treated as a temporary source failure. Offline, Online and Idle are non-gaming states; retained artwork alone never activates an interruption. The artwork URL must belong to the configured Home Assistant origin. Redirects, artwork exceeding 12 MiB, and images over 20 million pixels are rejected. Those fixed safety limits are not user options.
