#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Install or update Game Display without changing InkyPi's core or settings."""
import argparse
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def parsed(path):
    try:
        return ast.parse(path.read_text())
    except (OSError, SyntaxError) as error:
        raise ValueError(f'Cannot read compatible source: {path}') from error


def has_function(tree, name):
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
               for node in ast.walk(tree))


def check(root):
    src = root / 'src'
    failures = []
    requirements = {
        'plugins/plugin_registry.py': ['register_plugin_blueprints', 'load_plugins', 'get_plugin_instance'],
        'blueprints/apikeys.py': ['get_env_path', 'apikeys_page', 'save_apikeys'],
        'config.py': ['load_env_key', 'get_config', 'get_resolution'],
        'refresh_task.py': ['_determine_next_plugin', 'signal_config_change', 'manual_update'],
    }
    for filename, functions in requirements.items():
        try:
            tree = parsed(src / filename)
            for function in functions:
                if not has_function(tree, function):
                    failures.append(f'{filename}: missing {function}')
        except ValueError as error:
            failures.append(str(error))
    try:
        app = parsed(src / 'inkypi.py')
        if not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == 'register_plugin_blueprints' for node in ast.walk(app)):
            failures.append('inkypi.py: plugin blueprints are not registered')
    except ValueError as error:
        failures.append(str(error))
    return failures


def locate(explicit=None):
    candidates = [Path(explicit).expanduser()] if explicit else [
        Path('/usr/local/inkypi'), Path.home() / 'InkyPi', Path('/opt/inkypi')]
    roots = sorted({(candidate / 'src').resolve().parent for candidate in candidates
                    if (candidate / 'src/inkypi.py').is_file()})
    if not roots:
        raise ValueError('InkyPi not found. Pass --inkypi-dir /path/to/InkyPi.')
    if len(roots) != 1:
        raise ValueError('Multiple InkyPi installations found. Select one with --inkypi-dir.')
    return roots[0]


def install(root, package=PACKAGE, restart=True):
    failures = check(root)
    if failures:
        raise ValueError('Compatibility check failed:\n  '+ '\n  '.join(failures))
    source = package / 'plugins/game_display'
    manifest = json.loads((source / 'plugin-info.json').read_text())
    if manifest.get('id') != 'game_display':
        raise ValueError('The release package has an invalid plugin ID')
    for path in source.glob('*.py'):
        compile(path.read_text(), str(path), 'exec')
    plugins = root / 'src/plugins'
    destination = plugins / 'game_display'
    backup = None
    if destination.exists():
        current = json.loads((destination / 'plugin-info.json').read_text())
        if current.get('id') != 'game_display':
            raise ValueError('Existing destination is not Game Display; refusing to replace it')
        backups = root / 'src/config/game_display/plugin-backups'
        backups.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = backups / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    was_running = False
    if restart:
        if not shutil.which('systemctl'):
            raise ValueError('systemctl is unavailable; use --no-restart and restart InkyPi yourself')
        was_running = subprocess.run(['systemctl', 'is-active', '--quiet', 'inkypi.service']).returncode == 0
    with tempfile.TemporaryDirectory(prefix='game-display-install-') as temporary:
        staged = Path(temporary) / 'game_display'
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        # Finish the backup before touching the working copy. A failed backup
        # must leave the old plugin intact.
        if backup:
            shutil.copytree(destination, backup, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if was_running:
            subprocess.run(['systemctl', 'stop', 'inkypi.service'], check=True)
        try:
            if backup:
                shutil.rmtree(destination)
            shutil.copytree(staged, destination)
        except Exception:
            if destination.exists():
                shutil.rmtree(destination)
            if backup and backup.exists():
                shutil.copytree(backup, destination)
            raise
        finally:
            if was_running:
                subprocess.run(['systemctl', 'start', 'inkypi.service'], check=True)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inkypi-dir', help='InkyPi project directory (containing src/)')
    parser.add_argument('--check', action='store_true', help='Check compatibility without changing files')
    parser.add_argument('--dry-run', action='store_true', help='Show the installation plan without changing files')
    parser.add_argument('--no-restart', action='store_true', help='Do not use systemd; restart InkyPi manually')
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        parser.exit(1, 'Python 3.9 or later is required.\n')
    try:
        root = locate(args.inkypi_dir)
        failures = check(root)
        if failures:
            raise ValueError('Unsupported InkyPi build:\n  '+'\n  '.join(failures)+'\nSee docs/COMPATIBILITY.md. No files changed.')
        print(f'Compatible source interfaces found: {root}')
        if args.check:
            return
        print(f'Install Game Display {(PACKAGE / "VERSION").read_text().strip()} into {root / "src/plugins/game_display"}')
        print('Preserve all configuration, API keys and other services.')
        if args.dry_run:
            print('Dry run: no files changed.')
            return
        backup = install(root, restart=not args.no_restart)
        print('Installed. Open Game Display in the InkyPi web interface.')
        if backup:
            print(f'Previous plugin backup: {backup}')
        if args.no_restart:
            print('Restart InkyPi manually to load the new code.')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
