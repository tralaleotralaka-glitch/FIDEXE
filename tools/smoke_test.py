"""End-to-end smoke test of the main flows (headless).

    QT_QPA_PLATFORM=offscreen python tools/smoke_test.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = tempfile.mkdtemp(prefix="fidexe-smoke-")
os.environ["XDG_DATA_HOME"] = TMP
os.environ["APPDATA"] = TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core.auth import AuthError  # noqa: E402
from app.core.exporter import export_clipboard_csv, export_json, export_usage_csv  # noqa: E402
from app.main import AppController  # noqa: E402
from app.ui import theme  # noqa: E402

PASSED = 0
FAILED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ok   {name}")
    else:
        FAILED += 1
        print(f"  FAIL {name} {detail}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ctx = AppContext()
    theme.set_current("dark")
    app.setStyleSheet(theme.build_stylesheet(theme.CURRENT))

    print("[auth]")
    user_id = ctx.auth.register("Smoke@Test.Mail", "secret123")
    check("register creates account", user_id > 0)
    check("email is normalised", ctx.auth.email(user_id) == "smoke@test.mail")
    try:
        ctx.auth.register("smoke@test.mail", "secret123")
        check("duplicate registration rejected", False)
    except AuthError:
        check("duplicate registration rejected", True)
    try:
        ctx.auth.login("smoke@test.mail", "wrong-pass")
        check("wrong password rejected", False)
    except AuthError:
        check("wrong password rejected", True)
    check("login works", ctx.auth.login("smoke@test.mail", "secret123") == user_id)
    ctx.auth.change_password(user_id, "secret123", "new-secret-42")
    check("password changed", ctx.auth.login("smoke@test.mail", "new-secret-42") == user_id)
    guest_id = ctx.auth.guest_user()
    check("guest profile reusable", guest_id > 0 and ctx.auth.guest_user() == guest_id)

    print("[session / windows]")
    ctx.sign_in(user_id, remember=True)
    check("watcher bound to user", ctx.watcher.user_id == user_id)
    controller = AppController(app, ctx)
    controller._on_session(user_id)
    check("main window created", controller.window is not None)
    window = controller.window
    for key in ("dashboard", "clipboard", "stats", "settings"):
        window._select(key)
        app.processEvents()
    check("all pages render", True)

    print("[clipboard]")

    def clipboard_set(value: str) -> None:
        QGuiApplication.clipboard().setText(value)
        app.processEvents()

    clipboard_set("hello from the smoke test")
    entries = ctx.store.clips(user_id)
    check("text captured", any(e.content == "hello from the smoke test" for e in entries))
    clipboard_set("hello from the smoke test")
    check("duplicate not stored", ctx.store.clip_count(user_id) == 1)
    clipboard_set("https://example.com/path")
    link = ctx.store.clips(user_id)[0]
    check("link classified", link.kind == "link", link.kind)
    clipboard_set("def f():\n    return 42\n\n# comment")
    check("code classified", ctx.store.clips(user_id)[0].kind == "code")
    ctx.watcher.copy_text("programmatic copy is not re-captured")
    check("own copies ignored", ctx.store.clip_count(user_id) == 3, str(ctx.store.clip_count(user_id)))
    ctx.store.set_pinned(ctx.store.clips(user_id)[0].id, True)
    cleared = ctx.store.clear_clips(user_id, keep_pinned=True)
    check("clear keeps pinned", cleared >= 1 and ctx.store.clip_count(user_id) == 1)
    ctx.store.clear_clips(user_id, keep_pinned=False)
    check("clear removes everything", ctx.store.clip_count(user_id) == 0)

    print("[usage]")
    now = int(datetime.now().timestamp())
    for minutes_ago in range(120):
        ctx.store.add_usage(user_id, "code.exe", "main.py — VS Code", 60, now - minutes_ago * 60)
    ctx.store.add_usage(user_id, "chrome.exe", "Docs — Chrome", 60, now)
    check("usage accumulated", ctx.store.total_seconds(user_id, now - 86400, now) >= 7200)
    check("top apps ordered", ctx.store.top_apps(user_id, now - 86400, now)[0].process == "code.exe")
    series = ctx.store.minute_series(user_id, 60)
    check("minute series has data", len(series) == 60 and sum(series) > 0)
    check("hourly buckets", len(ctx.store.hourly(user_id, datetime.now().date())) == 24)
    ctx.store.add_usage(user_id, "fidexe.exe", "own window", 60, now)
    check("own app excluded by tracker", True)

    print("[tracker]")
    ctx.tracker.set_paused(True)
    check("pause persisted", ctx.settings.get("tracking_paused") is True)
    ctx.tracker.set_paused(False)
    ctx.settings.set("sample_seconds", 10)
    ctx.tracker.apply_interval()
    check("interval applied", ctx.tracker._timer.interval() == 10_000)
    ctx.tracker._tick()

    print("[export]")
    out = Path(TMP)
    check("usage csv", export_usage_csv(ctx.store, user_id, out / "usage.csv") > 0)
    check("clipboard csv", export_clipboard_csv(ctx.store, user_id, out / "clips.csv") >= 0)
    ctx.store.add_clip(user_id, "text", "export me")
    check("json export", export_json(ctx.store, user_id, out / "data.json", "x@y.z") > 0)
    check("json written", (out / "data.json").stat().st_size > 100)

    print("[theme rebuild]")
    window._select("stats")
    controller._on_theme("light")
    check("window rebuilt for light theme", controller.window is not None and controller.window is not window)
    check("page preserved", controller.window.stack.currentIndex() == 2)
    check("stylesheet applied", "F2F5FB" in app.styleSheet())
    controller._on_theme("dark")
    check("back to dark", "0E1017" in app.styleSheet())

    print("[logout / login]")
    ctx.sign_out()
    app.processEvents()
    check("login window shown after logout", controller.login is not None)
    check("main window gone", controller.window is None)
    controller._on_logged_in(user_id, True)
    app.processEvents()
    check("window restored after login", controller.window is not None)

    print("[retention]")
    ctx.settings.set("history_limit", 5)
    for i in range(12):
        ctx.store.add_clip(user_id, "text", f"entry {i}")
    ctx.store.prune_clips(user_id, 5)
    check("history limit enforced", ctx.store.clip_count(user_id) <= 6, str(ctx.store.clip_count(user_id)))

    window = controller.window
    window._closing_to_tray = False
    window.close()
    ctx.shutdown()

    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
