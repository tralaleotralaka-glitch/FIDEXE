"""Tiny persistent settings store (JSON on disk)."""
from __future__ import annotations

import json
import os
from typing import Any

from .paths import settings_path

DEFAULTS: dict[str, Any] = {
    "theme": "dark",              # dark | light
    "sample_seconds": 5,          # how often the foreground app is sampled
    "history_limit": 500,         # max clipboard rows kept per user (0 = unlimited)
    "autostart": False,           # launch with Windows
    "close_to_tray": True,        # X button minimises to tray
    "start_minimized": False,
    "tracking_paused": False,
    "idle_seconds": 120,          # ignore "usage" while the user is away
    "excluded_apps": "lockapp.exe, searchapp.exe, dwm.exe",
    "capture_images": True,       # store copied images on disk
    "prune_days": 120,            # drop usage details older than this
    "session_user": 0,            # remembered user id (0 = signed out)
    "notify_on_copy": False,
    "remote_enabled": False,      # LAN control endpoint for the Android app
    "remote_port": 47811,
    "camera_allowed": False,      # let the phone watch this PC's webcam
}


class Settings:
    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        path = settings_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if key in DEFAULTS:
                        self._data[key] = value
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        path = settings_path()
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any]) -> None:
        self._data.update(values)
        self.save()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
