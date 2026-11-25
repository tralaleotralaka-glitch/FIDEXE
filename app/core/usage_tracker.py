"""Periodic foreground-app sampler that writes to the usage table."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from . import tracker
from .db import Storage
from .settings import Settings

OWN_NAMES = {"fidexe.exe", "fidexe", "python.exe", "pythonw.exe", "python3"}


class UsageTracker(QObject):
    """Samples the active window every N seconds and stores the elapsed time."""

    changed = Signal(str, str)     # process, title
    idle_changed = Signal(bool)

    def __init__(self, store: Storage, settings: Settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.settings = settings
        self.user_id = 0
        self.paused = bool(settings.get("tracking_paused", False))
        self._idle = False
        self._last_sample = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self.apply_interval()

    # ------------------------------------------------------------------ api
    def apply_interval(self) -> None:
        seconds = max(1, int(self.settings.get("sample_seconds", 5)))
        self._timer.start(seconds * 1000)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self.settings.set("tracking_paused", paused)
        if paused:
            self._last_sample = time.monotonic()

    def set_user(self, user_id: int) -> None:
        self.user_id = user_id
        self._last_sample = time.monotonic()

    def _excluded(self, process: str) -> bool:
        raw = str(self.settings.get("excluded_apps", "") or "")
        names = {part.strip().lower() for part in raw.replace(";", ",").split(",") if part.strip()}
        names |= OWN_NAMES
        lowered = process.lower()
        return lowered in names or (lowered.endswith(".exe") and lowered[:-4] in names)

    def _tick(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_sample
        self._last_sample = now
        interval = max(1, int(self.settings.get("sample_seconds", 5)))

        if not self.user_id or self.paused:
            return
        idle_limit = max(15, int(self.settings.get("idle_seconds", 120)))
        if tracker.is_supported():
            idle = tracker.idle_seconds() > idle_limit
            if idle != self._idle:
                self._idle = idle
                self.idle_changed.emit(idle)
            if idle:
                return

        sample = tracker.foreground()
        if sample is None:
            if not tracker.is_supported():
                # Linux/macOS dev builds have no Win32 API: show status, store nothing.
                self.changed.emit("fidexe.exe", "Демо-режим: трекинг активных окон доступен в Windows")
            return
        process, title = sample
        if self._excluded(process):
            return
        seconds = int(min(elapsed, interval * 2.2)) or interval
        self.store.add_usage(self.user_id, process, title, seconds)
        self.changed.emit(process, title)

    def shutdown(self) -> None:
        self._timer.stop()
