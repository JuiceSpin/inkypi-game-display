#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Build deterministic, source-complete release archives without local settings."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ['README.md', 'LICENSE', 'NOTICE', 'VERSION', 'CHANGELOG.md', 'requirements-dev.txt', '.gitignore']
TREES = ['plugins/game_display', 'docs', 'scripts', 'tests', 'tools', 'releases']


def files():
    paths = [ROOT / name for name in TOP_FILES]
    for directory in TREES:
        paths.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    for path in sorted(paths):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or unsafe release file: {path}')
        if path.name in {'.env', 'ha-token', 'settings.json', 'controls.json', 'previous.png', 'override-active'}:
            raise ValueError(f'Private runtime file in release source: {path}')
        yield path


def build(destination=None):
    version = (ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION must contain a semantic version')
    manifest = json.loads((ROOT/'plugins/game_display/plugin-info.json').read_text())
    if manifest.get('version') != version:
        raise ValueError('Plugin metadata version differs from VERSION')
    if 'GNU GENERAL PUBLIC LICENSE' not in (ROOT/'LICENSE').read_text():
        raise ValueError('Release licence is missing')
    out = Path(destination) if destination else ROOT/'dist'
    out.mkdir(parents=True, exist_ok=True)
    name = 'inkypi-game-display-'+version
    content = [(name+'/'+str(path.relative_to(ROOT)), path.read_bytes(),
                0o755 if path.relative_to(ROOT).parts[0]=='scripts' and path.suffix=='.py' else 0o644)
               for path in files()]
    zip_path = out/(name+'.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry, data, mode in content:
            info=zipfile.ZipInfo(entry, (2026, 11, 6, 0, 0, 0))
            info.create_system=3
            info.external_attr=(0o100000 | mode) << 16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    tar_bytes=io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for entry, data, mode in content:
            info=tarfile.TarInfo(entry)
            info.size=len(data);info.mode=mode;info.mtime=0
            info.uid=info.gid=0;info.uname=info.gname=''
            archive.addfile(info, io.BytesIO(data))
    tar_path=out/(name+'.tar.gz')
    with tar_path.open('wb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as compressed:
            compressed.write(tar_bytes.getvalue())
    sums=''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in [zip_path,tar_path])
    (out/'SHA256SUMS').write_text(sums)
    return [zip_path, tar_path, out/'SHA256SUMS']


if __name__=='__main__':
    for path in build():
        print(path)
