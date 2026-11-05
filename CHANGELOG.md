# Changelog

## 0.1.0 — 2026-11-06

First standalone release of Game Display for InkyPi.

- Automatically display game artwork from a Home Assistant Gaming Status master sensor.
- Prefer Xbox titled hero art, keeping it stable for the session.
- Compose PC artwork from a hero image and logo, with a title fallback.
- Resume the current scheduled playlist or restore the previous image after gaming.
- Include an interruption switch and a weekly, hourly schedule in InkyPi's timezone.
- Configure the HA connection, platform entities, timings, artwork, layout and attribute mappings through the plugin UI.
- Store the Home Assistant token in InkyPi API Keys as `HOME_ASSISTANT_TOKEN`.
- Test the saved connection without showing credentials.
- Confirm session end using optional raw PC, Steam and Xbox sources.
- Deduplicate display writes and preserve restart recovery information.

### Compatibility

Requires InkyPi's plugin blueprint registration extension and native API-key interface. The installer checks these capabilities before changing files. A default upstream checkout without the registration extension is not supported by this release.

Tested on a Pimoroni Inky Impression 7.3-inch (2025) display, landscape, with Steam and Epic PC games and Xbox console games. Artwork display, switching games, stable Xbox artwork and normal playlist restoration were confirmed on the physical screen. Scheduling, settings and failure behaviour have automated coverage; other hardware has not been physically tested.
