# Development and release process

## Tests

Use Python 3.9 or later. In a fresh virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH="$PWD/plugins" python -m unittest discover -s tests -v
```

The tests provide minimal InkyPi interfaces when no InkyPi checkout is on the Python path. To test against a real checkout's supporting modules, append its `src/` directory to `PYTHONPATH`. The scheduler and panel remain simulated in the unit tests.

The optional browser test requires Chromium's `chromium-headless-shell`:

```bash
PYTHONPATH="$PWD/plugins" python tools/check_controls_ui.py
```

It uses a temporary server and settings, and does not change live controls. Do not run it on a public listening interface.

## Versioning

`VERSION`, `plugins/game_display/plugin-info.json`, the changelog and release notes must agree. Versions follow `MAJOR.MINOR.PATCH`; the Git tag is `vMAJOR.MINOR.PATCH`.

## Build a release

Run tests first, then:

```bash
python3 scripts/build_release.py
```

This produces a ZIP, tar.gz and `SHA256SUMS` in `dist/`. Both archives contain the complete source, tests, documentation, installer and licence. A fixed file order, archive timestamps and gzip header make repeated builds of the same source reproducible.

Packaging uses an explicit source allowlist. Runtime settings, `.env`, tokens, display snapshots, backups, the Git directory and Python caches must never be added to that allowlist. Release tests check archive completeness and reproducibility.

## Publish

Commit the reviewed source and create the matching tag. Attach the two archives and `SHA256SUMS` to the GitHub release, using the notes in `releases/vVERSION.md`. Verify the published assets and their checksums before announcing the release.

The compatibility checker is deliberately conservative. Changes to InkyPi's worker lifecycle need targeted testing; do not remove the check merely to make an unsupported build install.
