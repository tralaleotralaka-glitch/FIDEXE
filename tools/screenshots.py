"""Render every screen with demo data into PNG files (used for visual checks).

    QT_QPA_PLATFORM=offscreen python tools/screenshots.py [outdir]
"""
from __future__ import annotations

import os
import random
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# isolate demo data from the real profile
os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="fidexe-shots-"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core.db import Storage  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.login import LoginWindow  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots")

APPS = [
    ("chrome.exe", "GitHub · FIDEXE", 0.30),
    ("code.exe", "main.py — Visual Studio Code", 0.26),
    ("telegram.exe", "Telegram", 0.14),
    ("excel.exe", "Отчёт Q4.xlsx — Excel", 0.10),
    ("explorer.exe", "Загрузки", 0.08),
    ("spotify.exe", "Spotify Premium", 0.06),
    ("zoom.exe", "Созвон с командой — Zoom", 0.06),
]

CLIPS = [
    ("code", "def build_overview(store, user_id, period='week'):\n    today = date.today()\n    start, end = period_bounds(period, today)\n    return Overview(...)", 6),
    ("link", "https://github.com/tralaleotralaka-glitch/FIDEXE", 18),
    ("text", "Спасибо за встречу! Скинул макеты в общую папку — посмотри до пятницы.", 42),
    ("text", "Пароль от Wi-Fi: cafe-guest-2024 (действует до конца дня)", 95),
    ("link", "https://www.fide.com/ratings", 140),
    ("code", "SELECT day, SUM(seconds) AS s FROM usage WHERE user_id = ? GROUP BY day;", 210),
    ("text", "Иван Петров\nivan@example.com\n+7 999 123-45-67", 300),
    ("text", "Адрес доставки: Москва, ул. Тверская, 12, кв. 45, подъезд 2", 420),
    ("link", "https://docs.python.org/3/library/sqlite3.html", 560),
    ("text", "Не забыть: продлить домен, оплатить хостинг, ответить на письмо от Анны", 780),
    ("code", "git commit -m 'feat: clipboard history + usage charts'", 940),
    ("text", "Рецепт: 3 яйца, 200 мл молока, 150 г муки, щепотка соли", 1500),
]


def seed(store: Storage) -> int:
    from app.core.auth import AuthService

    auth = AuthService(store)
    email = "demo@fidexe.app"
    row = store.find_user(email)
    if row:
        return int(row["id"])
    user_id = auth.register(email, "fidexe-demo-2024")

    rng = random.Random(42)
    today = date.today()
    now = datetime.now()
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        weekday = day.weekday()
        base_minutes = rng.randint(240, 420) if weekday < 5 else rng.randint(60, 180)
        end_minute = 23 * 60 if offset else min(now.hour * 60 + now.minute, 23 * 60)
        start_minute = 8 * 60
        for minute in range(start_minute, min(start_minute + base_minutes, end_minute)):
            if rng.random() < 0.18:
                continue
            progress = (minute - start_minute) / max(1, base_minutes)
            if progress < 0.15 or progress > 0.92:
                if rng.random() < 0.55:
                    continue
            pick = rng.random()
            acc = 0.0
            chosen = APPS[0]
            for app in APPS:
                acc += app[2]
                if pick <= acc:
                    chosen = app
                    break
            moment = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)
            store.add_usage(user_id, chosen[0], chosen[1], 60, int(moment.timestamp()))

    for kind, text, minutes_ago in CLIPS:
        store.add_clip(user_id, kind, text, "", int(time.time()) - minutes_ago * 60)
    store.set_pinned(2, True)
    store.add_clip(user_id, "text", "Точка входа: app/main.py — запускать через python main.py", "", int(time.time()) - 30)
    return user_id


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    ctx = AppContext()
    user_id = seed(ctx.store)
    theme.set_current("dark")
    app.setStyleSheet(theme.build_stylesheet(theme.CURRENT))
    ctx.sign_in(user_id, True)
    latest = ctx.store.latest_usage(user_id)
    if latest:
        ctx.tracker.changed.emit(latest["process"], latest["title"] or "")

    login = LoginWindow(ctx)
    login.show()
    app.processEvents()
    login.grab().save(str(OUT / "login.png"))
    login.hide()

    window = MainWindow(ctx)
    window.resize(1320, 860)
    window.show()
    for page_key in ("dashboard", "clipboard", "stats", "settings"):
        window._select(page_key)
        for _ in range(3):
            app.processEvents()
        window.grab().save(str(OUT / f"{page_key}.png"))

    # light theme variant of the dashboard
    theme.set_current("light")
    app.setStyleSheet(theme.build_stylesheet(theme.CURRENT))
    light = MainWindow(ctx)
    light.resize(1320, 860)
    light.show()
    light._select("dashboard")
    for _ in range(3):
        app.processEvents()
    light.grab().save(str(OUT / "dashboard_light.png"))
    light._select("stats")
    for _ in range(3):
        app.processEvents()
    light.grab().save(str(OUT / "stats_light.png"))

    print("saved to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
