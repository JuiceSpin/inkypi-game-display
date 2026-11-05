# Troubleshooting

| Symptom | What to check |
| --- | --- |
| Installer says unsupported | Read the missing capability in its output. This release needs the plugin blueprint registration extension and native API-key interface; see [Compatibility](COMPATIBILITY.md). |
| Plugin is absent after installation | Restart only InkyPi. Check `sudo journalctl -u inkypi -n 60 --no-pager` for import or registration errors. |
| API key says Not configured | Add `HOME_ASSISTANT_TOKEN` through InkyPi API Keys and save. The name is case-sensitive. Refresh the plugin page. |
| Connection test rejects the key | Use a valid Home Assistant long-lived access token, not an MQTT password. Replace it through API Keys. |
| Cannot reach Home Assistant | Use a URL reachable from the Pi. A URL working on your phone can still be inaccessible from the Pi or resolve differently. Include the HA port when needed. |
| Connection redirects | Use the direct HA base URL rather than a dashboard, login page or redirecting hostname. |
| Entity Not found | Copy the exact entity ID from Home Assistant States. The display name is not the entity ID. |
| Xbox entities show unknown while idle | This can be normal. Start a console game and test again. Missing/disabled entities need fixing separately. |
| Master remains Offline during a console game | Enable the native Xbox Status entity if disabled, and select it in Gaming Status. Check the master before troubleshooting the display. |
| Correct game in HA, no interruption | Confirm the global switch is on and the current hour is allowed when scheduling is enabled. Save grid edits. |
| Art takes time to appear | Allow HA detection, one poll interval and the panel refresh. Lowering the poll interval does not shorten an e-ink refresh already underway. |
| Art remains after closing the game | Gaming Status has grace periods. Configure every raw source you use for faster release; see [Installation](INSTALLATION.md#optional-faster-clearing-after-play-ends). |
| Artwork is missing | Check artwork attributes in Gaming Status and its artwork-provider configuration. The plugin falls back to cover art or a title card. |
| Xbox art changes to a worse image | Enable Prefer Xbox titled hero artwork and Keep preferred Xbox artwork for the session. Check the live Xbox title matches the master. |
| A title or logo is cropped | Use Fit whole image. Reduce logo dimensions or font size and check padding. Titles embedded in the source artwork cannot be moved separately. |
| Schedule seems shifted | Check InkyPi's configured timezone, then the timezone displayed beside the grid. Hours are local wall-clock times. |
| Old UI after an update | Refresh the page or clear the browser cache. New code requires an InkyPi restart; preference changes do not. |

## Reporting a problem

Include the plugin version, InkyPi version or commit, display model, whether the compatibility check passed, the action that triggered the problem, and the relevant log lines. Share entity IDs, states and non-secret attribute names if needed.

Do not share the Home Assistant token, the native `.env` file, image proxy access tokens or unredacted diagnostics. Full source logs can include information from other plugins; review them before posting an issue.
