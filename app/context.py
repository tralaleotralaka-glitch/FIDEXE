"""Application context: shared services and cross-window signals."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

import time
from datetime import date, datetime

from .core.auth import AuthService
from .core.clipboard_watch import ClipboardWatcher
from .core.db import Storage
from .core.remote import RemoteControl
from .core.settings import Settings
from .core.usage_tracker import UsageTracker


class AppContext(QObject):
    session_changed = Signal(int)      # user id, 0 = signed out
    theme_changed = Signal(str)
    toast = Signal(str, str)           # message, kind (ok | warn | error)
    status_changed = Signal(bool)      # tracking active

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.store = Storage()
        self.auth = AuthService(self.store)
        self.watcher = ClipboardWatcher(
            self.store, capture_images=bool(self.settings.get("capture_images", True))
        )
        self.tracker = UsageTracker(self.store, self.settings)
        self.user_id = 0
        self._shutdown = False
        self.watcher.attach()

        self.remote = RemoteControl(self.store, self._remote_status)
        self.remote.locked.connect(self._on_remote_lock)
        self.remote.client_authenticated.connect(self._on_remote_client)
        self.remote.command_done.connect(self._on_remote_command)
        self.remote.failed_attempt.connect(self._on_remote_failure)

    # ------------------------------------------------------------- session
    def sign_in(self, user_id: int, remember: bool = True) -> None:
        self.user_id = user_id
        self.watcher.user_id = user_id
        self.tracker.set_user(user_id)
        self.settings.set("session_user", user_id if remember else 0)
        self.store.prune_clips(user_id, int(self.settings.get("history_limit", 500)))
        self.store.prune_usage(user_id, int(self.settings.get("prune_days", 120)))
        self.session_changed.emit(user_id)

    def sign_out(self) -> None:
        self.user_id = 0
        self.watcher.user_id = 0
        self.tracker.set_user(0)
        self.settings.set("session_user", 0)
        self.session_changed.emit(0)

    @property
    def email(self) -> str:
        return self.auth.email(self.user_id) if self.user_id else ""

    @property
    def user_initial(self) -> str:
        email = self.email
        return (email[:1] or "?").upper()

    # ------------------------------------------------------------- theme
    def set_theme(self, name: str) -> None:
        self.settings.set("theme", name)
        self.theme_changed.emit(name)

    # ------------------------------------------------------ remote control
    def _remote_status(self, user_id: int) -> dict:
        now = int(time.time())
        start = int(datetime.combine(date.today(), datetime.min.time()).timestamp())
        latest = self.store.latest_usage(user_id)
        top = self.store.top_apps(user_id, start, now, 3)
        return {
            "today_seconds": self.store.total_seconds(user_id, start, now),
            "current_app": latest["process"] if latest else "",
            "current_title": (latest["title"] or "") if latest else "",
            "top_apps": [{"app": a.process, "seconds": a.seconds} for a in top],
            "clip_count": self.store.clip_count(user_id),
            "paused": bool(self.settings.get("tracking_paused", False)),
            "tracking": not bool(self.settings.get("tracking_paused", False)),
        }

    @property
    def remote_enabled(self) -> bool:
        return bool(self.settings.get("remote_enabled", False))

    def start_remote(self) -> bool:
        if self.remote.running:
            return True
        ok = self.remote.start(int(self.settings.get("remote_port", 47811)))
        self.settings.set("remote_enabled", ok)
        return ok

    def stop_remote(self) -> None:
        self.remote.stop()
        self.settings.set("remote_enabled", False)

    def set_remote_enabled(self, enabled: bool) -> bool:
        if enabled:
            return self.start_remote()
        self.stop_remote()
        return True

    def _on_remote_lock(self, device: str) -> None:
        self.toast.emit(f"Ноутбук заблокирован с телефона ({device})", "ok")

    def _on_remote_client(self, email: str, device: str) -> None:
        self.toast.emit(f"Телефон подключён: {device}", "ok")

    def _on_remote_failure(self, client: str) -> None:
        self.toast.emit("Неудачная попытка входа с телефона", "warn")

    def _on_remote_command(self, cmd: str, device: str) -> None:
        if cmd == "pause":
            self.set_tracking_paused(True)
            self.toast.emit("Трекинг приостановлен с телефона", "warn")
        elif cmd == "resume":
            self.set_tracking_paused(False)
            self.toast.emit("Трекинг включён с телефона", "ok")

    # ------------------------------------------------------------ helpers
    def refresh_clipboard_settings(self) -> None:
        self.watcher.capture_images = bool(self.settings.get("capture_images", True))

    def set_tracking_paused(self, paused: bool) -> None:
        self.tracker.set_paused(paused)
        self.status_changed.emit(not paused)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.remote.stop()
        self.tracker.shutdown()
        self.settings.save()
        self.store.close()
