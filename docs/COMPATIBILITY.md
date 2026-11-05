# Compatibility

Game Display is an automatic interruption plugin. Ordinary InkyPi image plugins are invoked by a playlist; this plugin also needs to register routes and attach to the existing scheduler.

## Required capabilities

- Python 3.9 or later, with InkyPi's Flask, requests, Pillow and python-dotenv dependencies.
- `plugins/plugin_registry.py` defines `register_plugin_blueprints` and `inkypi.py` calls it after storing application dependencies.
- `blueprints/apikeys.py` exposes the native API Keys interface and `get_env_path`.
- `Config` has `load_env_key`, `get_config` and `get_resolution`.
- `RefreshTask` has `_determine_next_plugin`, `signal_config_change`, and `manual_update`, plus the installed refresh worker's playlist/plugin interfaces.
- Home Assistant Gaming Status master sensor attributes, or equivalent attributes mapped through the advanced settings.

The release installer checks the source-level capabilities it can establish safely without starting the app or touching the display. It cannot prove runtime compatibility with every fork. A successful check is a prerequisite, not a replacement for the first live test.

The working installation used to develop this plugin is based on InkyPi revision `df5fac46274a54b682f557a8ad4cde05dc41679a` with the generic plugin blueprint registration extension. That revision alone does not guarantee compatibility: the extension must also be present. This release does not advertise support for an unmodified upstream checkout lacking that extension.

If the compatibility check fails, retain your working installation and check whether your InkyPi build provides these extension points. Do not bypass the check or paste scheduler patches from an unrelated version. Supporting a different InkyPi plugin lifecycle may require a separate adapter.

Display resolution, orientation, image enhancement and timezone are inherited from InkyPi. Hardware support follows InkyPi's own drivers. Physical testing for this release used the Pimoroni Inky Impression 7.3-inch (2025), in landscape. Other panel sizes may need logo and title layout adjustments.
