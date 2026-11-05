# Installation and first setup

## Before you start

You need a working InkyPi display and Home Assistant with Gaming Status already showing the current game for your player. You do not need to install the Gaming Status Agent on the display Pi: it belongs on your gaming PC.

This release requires InkyPi's native API Keys page and plugin blueprint registration extension. The installer checks the exact capabilities needed. It does not silently modify your InkyPi application or scheduler to add them. If the check fails, see [Compatibility](COMPATIBILITY.md).

## 1. Install the plugin

Download and extract [`inkypi-game-display-0.1.0.zip`](https://github.com/JuiceSpin/inkypi-game-display/releases/download/v0.1.0/inkypi-game-display-0.1.0.zip) on the Pi, then open a terminal in the extracted directory:

```bash
python3 scripts/install.py --check
sudo python3 scripts/install.py
```

The installer locates common InkyPi installations, checks compatibility, backs up an existing plugin, installs the new version and restarts only `inkypi.service` if it was already running. It preserves settings, schedules, credentials and other services.

If you prefer downloading from the Pi terminal:

```bash
curl --fail --location --output inkypi-game-display-0.1.0.zip https://github.com/JuiceSpin/inkypi-game-display/releases/download/v0.1.0/inkypi-game-display-0.1.0.zip
unzip inkypi-game-display-0.1.0.zip
cd inkypi-game-display-0.1.0
python3 scripts/install.py --check
sudo python3 scripts/install.py
```

If it cannot locate InkyPi, specify its directory:

```bash
sudo python3 scripts/install.py --inkypi-dir /path/to/InkyPi
```

For a non-systemd installation, use `--no-restart` and restart InkyPi in your usual way. `--dry-run` shows the plan without installing. If multiple installations are found, select one explicitly. You do not need to install new Python packages in a supported InkyPi environment.

## 2. Add the Home Assistant token

1. Open Home Assistant using your normal account.
2. Open your profile, then **Security → Long-lived access tokens**.
3. Create a token named **InkyPi Game Display**, and copy it.
4. Open **InkyPi → API Keys → Add API Key**.
5. Enter `HOME_ASSISTANT_TOKEN` as the key name and paste the token as its value. Save.

The token stays in InkyPi's native secret store. The Game Display settings page only reports whether it is configured. Keep the token out of screenshots, issue reports and configuration examples.

## 3. Set two connection fields

Open **InkyPi → Game Display → Connection & artwork settings**.

1. Set **Home Assistant URL** to the address the Pi can reach, such as `http://homeassistant.local:8123`. Use the base address, without `/api` or a dashboard path.
2. Set **Gaming Status master sensor** to your player's master entity ID.

To find it, open **Home Assistant → Settings → Tools → States** (called Developer tools in some versions), search for `gaming_status`, and find the player sensor that shows the game title. Copy its entity ID; do not use the general Anyone Gaming binary sensor.

Choose **Save settings**, then **Test saved connection**. A working idle player may show Offline. Optional Xbox image or now-playing entities can show unknown when the console is idle; this does not by itself mean the token is invalid.

That is the minimum setup. Leave the remaining options at their defaults to start.

## Optional: better Xbox artwork

Under **Optional platform sensors**, set:

- **Xbox now-playing sensor:** the native Xbox sensor whose state is the live console game's title.
- **Xbox titled hero artwork:** the native Xbox image entity labelled Titled hero art.

Enable the Xbox integration's Status entity if it is disabled, and select it as the Xbox source in Gaming Status. Confirm the Gaming Status master sensor changes to the console game before troubleshooting the display.

The two artwork entities help match the title and image correctly. The defaults prefer this artwork and retain it for the session.

## Optional: faster clearing after play ends

Gaming Status deliberately retains sessions during grace periods. If you want the display to return sooner, configure every raw source you actually use:

- **PC agent sensor:** your Gaming Status Agent MQTT sensor.
- **Steam presence sensor:** the native Steam sensor with a `game` attribute.
- **Xbox in-game sensor:** the native Xbox binary sensor that is on while playing.

Leave unused platforms blank. All configured raw sources must confirm no game for 30 seconds by default. An unavailable source falls back to the master sensor. Changing this delay affects the display; it does not change Gaming Status's own grace periods.

## Optional: restrict when artwork can interrupt

In Game Display's main settings:

1. Leave **Allow game interruptions** on.
2. Turn on **Use weekly schedule**.
3. Clear the grid and click or drag across the hours you want to allow.
4. Choose **Save schedule**.

Rows are Monday–Sunday, columns are 00–23, and each cell covers one hour starting at its label. The schedule uses InkyPi's configured timezone. Turning the main switch off always prevents interruptions, regardless of the grid.

## First test

1. Start a game. Allow one polling interval, any upstream detection delay and the physical screen refresh.
2. Check the artwork. For Xbox, leave it running for a few minutes to check stability.
3. Close the game and confirm the normal playlist returns.
4. If using multiple platforms, test one game on each.
5. Switch interruptions off during a game, then back on. Test a closed schedule hour if using scheduling.

All settings and API-key changes apply without restarting InkyPi. E-ink refreshes already underway must finish first.

## Updating

Extract the newer release and run its installer. It backs up the existing plugin and preserves `src/config/game_display/` and the native API-key store. Check compatibility again after updating InkyPi itself.

## Rollback

The installer prints the previous-plugin backup directory. Turn off interruptions and let the normal playlist return. Stop InkyPi, replace only `src/plugins/game_display/` with that backup, then start InkyPi. Keep `src/config/game_display/` and the native API-key store intact. A newer configuration may need adjustment if an older release has a different settings schema.

## Uninstall

Turn off interruptions and let normal content return, stop InkyPi, remove `src/plugins/game_display/`, and restart InkyPi. You can then remove `src/config/game_display/` if you no longer need saved settings. Remove the HA token through API Keys only if no other plugin uses it; revoke it in Home Assistant when it is no longer needed.
