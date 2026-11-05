# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 JuiceSpin
"""Persistent interruption controls, independent of Home Assistant credentials."""
import json
import os
from pathlib import Path
import tempfile
import threading


class Controls:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    @staticmethod
    def defaults():
        return {'enabled': True, 'schedule_enabled': False,
                'hours': [[True] * 24 for _ in range(7)]}

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or set(data) != {'enabled', 'schedule_enabled', 'hours'}:
            raise ValueError('Expected interruption switch, schedule switch and weekly hours')
        if type(data['enabled']) is not bool or type(data['schedule_enabled']) is not bool:
            raise ValueError('Switch values must be true or false')
        hours = data['hours']
        if (not isinstance(hours, list) or len(hours) != 7 or
                any(not isinstance(row, list) or len(row) != 24 or
                    any(type(cell) is not bool for cell in row) for row in hours)):
            raise ValueError('Choose 24 hourly cells for each of seven days')
        return {key: data[key] for key in ('enabled', 'schedule_enabled', 'hours')}

    def read(self):
        with self.lock:
            if not self.path.exists():
                return self.defaults()
            return self.validate(json.loads(self.path.read_text()))

    def write(self, data):
        data = self.validate(data)
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.controls-', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w') as stream:
                    json.dump(data, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        return data

    def allows(self, now):
        data = self.read()
        return data['enabled'] and (not data['schedule_enabled'] or
                                   data['hours'][now.weekday()][now.hour])
