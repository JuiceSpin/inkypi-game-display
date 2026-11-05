"""Minimal InkyPi interfaces for running unit tests outside a Pi checkout."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import types

if importlib.util.find_spec('utils') is None:
    utils=types.ModuleType('utils');utils.__path__=[]
    images=types.ModuleType('utils.image_utils')
    images.compute_image_hash=lambda image: hashlib.sha256(image.tobytes()).hexdigest()
    app=types.ModuleType('utils.app_utils')
    app.resolve_path=lambda path: str(Path('/tmp/inkypi-test')/path)
    sys.modules.update({'utils':utils,'utils.image_utils':images,'utils.app_utils':app})

if importlib.util.find_spec('blueprints') is None:
    blueprints=types.ModuleType('blueprints');blueprints.__path__=[]
    keys=types.ModuleType('blueprints.apikeys')
    keys.get_env_path=lambda: '/tmp/inkypi-test/.env'
    sys.modules.update({'blueprints':blueprints,'blueprints.apikeys':keys})
