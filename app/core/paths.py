"""Filesystem locations used by the application."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "FIDEXE"
APP_TITLE = "FIDEXE"
APP_VERSION = "1.1.0"
APP_TAGLINE = "Буфер обмена и статистика активности"


def _base_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base)


def data_dir() -> Path:
    path = _base_data_dir() / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def images_dir() -> Path:
    path = data_dir() / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "fidexe.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource both in development and inside a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = Path(base) / relative
        if candidate.exists():
            return candidate
        return Path(base) / relative
    return Path(__file__).resolve().parent.parent / relative


def format_bytes(num: int) -> str:
    value = float(num)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if value < 1024 or unit == "ГБ":
            return f"{value:.0f} {unit}" if unit == "Б" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} ГБ"
