"""Dashboard: quick overview of today's activity and latest clipboard items."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...context import AppContext
from ...core.formatting import (
    app_initials,
    app_label,
    format_duration,
    short_title,
)
from .. import theme
from ..components import AppBadge, AppUsageRow, ClipRow
from ..widgets import Card, EmptyState, StatCard
from .base import Page


class StatusPill(QWidget):
    def __init__(self, active: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.active = active
        self.text = "Трекинг активен"
        self.setFixedHeight(32)
        self.setMinimumWidth(150)

    def set_active(self, active: bool, text: str | None = None) -> None:
        self.active = active
        if text:
            self.text = text
        elif active:
            self.text = "Трекинг активен"
        else:
            self.text = "Трекинг на паузе"
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.p["mint"] if self.active else self.p["warn"])
        soft = QColor(self.p["mint_soft"] if self.active else self.p["warn_soft"])
        painter.setPen(Qt.NoPen)
        painter.setBrush(soft)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 10, 10)
        painter.setBrush(color)
        painter.drawEllipse(QRectF(12, self.height() / 2 - 3.5, 7, 7))
        font = QFont(self.font())
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(QRectF(26, 0, self.width() - 34, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text)


class FocusCard(Card):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__("Сейчас в фокусе", "обновляется автоматически", "monitor", parent)
        self.ctx = ctx
        self.p = theme.CURRENT
        self.badge = AppBadge("FX", 44)
        self.app_name = QLabel("—")
        self.app_name.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.window_title = QLabel("Ожидание данных…")
        self.window_title.setObjectName("Subtitle")
        self.window_title.setWordWrap(True)
        self.window_title.setMinimumHeight(34)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self.badge, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.app_name)
        text.addWidget(self.window_title)
        row.addLayout(text, 1)
        self.body.addLayout(row)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {self.p['border_soft']};")
        self.body.addWidget(divider)

        self.time_value = QLabel("0 мин")
        self.time_value.setStyleSheet("font-size: 19px; font-weight: 700;")
        self.time_caption = QLabel("сегодня в этом приложении")
        self.time_caption.setObjectName("Subtitle")
        time_block = QVBoxLayout()
        time_block.setSpacing(1)
        time_block.addWidget(self.time_caption)
        time_block.addWidget(self.time_value)
        self.body.addLayout(time_block)

        self.spark_caption = QLabel("активность за последний час")
        self.spark_caption.setObjectName("Faint")
        self.body.addWidget(self.spark_caption)
        from ..charts import Sparkline

        self.spark = Sparkline()
        self.spark.setMinimumHeight(46)
        self.spark.setMaximumHeight(56)
        self.body.addWidget(self.spark)

        self.hint = QLabel("Приложения из списка исключений и время простоя не учитываются.")
        self.hint.setObjectName("Faint")
        self.hint.setWordWrap(True)
        self.body.addWidget(self.hint)

        self.current_process = ""
        self.current_title = ""

    def update_focus(self, process: str, title: str) -> None:
        self.current_process = process
        self.current_title = title
        self.badge.text = app_initials(process)
        self.badge.update()
        self.app_name.setText(app_label(process))
        self.window_title.setText(short_title(title, process, 120) or "Без названия окна")
        self.refresh_time()

    def refresh_time(self) -> None:
        if not self.current_process or not self.ctx.user_id:
            self.time_value.setText("0 мин")
            return
        start = int(datetime.combine(date.today(), datetime.min.time()).timestamp())
        seconds = self.ctx.store.app_seconds(self.ctx.user_id, self.current_process, start, int(datetime.now().timestamp()))
        self.time_value.setText(format_duration(seconds, compact=True))
        series = self.ctx.store.minute_series(self.ctx.user_id, 60)
        self.spark.set_data(series)
        has_data = any(series)
        self.spark.setVisible(has_data)
        self.spark_caption.setVisible(has_data)


class DashboardPage(Page):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self.p = theme.CURRENT
        greeting = self._greeting()
        self.add_header(greeting, self._date_line())

        self.status_pill = StatusPill(not ctx.settings.get("tracking_paused", False))
        self.add_header_action(self.status_pill)

        self.pause_button = QPushButton("Пауза")
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.add_header_action(self.pause_button)
        self._sync_pause_button()

        # stat cards -----------------------------------------------------
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_time = StatCard("Экран сегодня", "0 мин", "активное время с полуночи", "clock", "accent")
        self.card_clips = StatCard("Записей в буфере", "0", "всего сохранено", "clipboard", "mint")
        self.card_apps = StatCard("Приложений сегодня", "0", "уникальных окон", "apps", "blue")
        self.card_avg = StatCard("Время за неделю", "0 мин", "", "chart", "warn")
        for card in (self.card_time, self.card_clips, self.card_apps, self.card_avg):
            cards.addWidget(card, 1)
        self.v.addLayout(cards)

        # middle row -----------------------------------------------------
        middle = QHBoxLayout()
        middle.setSpacing(14)
        activity = Card("Активность за неделю", "суммарное время по дням", "chart")
        activity.setMinimumHeight(280)
        from ..charts import BarChart

        self.week_chart = BarChart()
        self.week_chart.setMinimumHeight(190)
        activity.add(self.week_chart, 1)
        middle.addWidget(activity, 2)

        self.focus = FocusCard(ctx)
        self.focus.setMinimumHeight(280)
        middle.addWidget(self.focus, 1)
        self.v.addLayout(middle)

        # bottom row -----------------------------------------------------
        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        self.clips_card = Card("Последние копии", "двойной клик — скопировать снова", "clipboard")
        self.clips_card.setMinimumHeight(300)
        self.clips_host = QVBoxLayout()
        self.clips_host.setSpacing(2)
        self.clips_card.body.addLayout(self.clips_host)
        self.clips_card.body.addStretch(1)
        bottom.addWidget(self.clips_card, 2)

        self.top_card = Card("Топ приложений сегодня", "по времени в фокусе", "apps")
        self.top_card.setMinimumHeight(312)
        self.top_host = QVBoxLayout()
        self.top_host.setSpacing(0)
        self.top_card.body.addLayout(self.top_host)
        self.top_card.body.addStretch(1)
        bottom.addWidget(self.top_card, 1)
        self.v.addLayout(bottom)
        self.v.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(20_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        ctx.tracker.changed.connect(self._on_usage)
        ctx.tracker.idle_changed.connect(self._on_idle)
        ctx.watcher.captured.connect(self._on_capture)
        ctx.status_changed.connect(self._on_status)
        self._restore_focus()

    # ------------------------------------------------------------- helpers
    def _greeting(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Доброе утро"
        if 12 <= hour < 18:
            return "Добрый день"
        if 18 <= hour < 23:
            return "Добрый вечер"
        return "Доброй ночи"

    def _date_line(self) -> str:
        today = date.today()
        months = (
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря",
        )
        weekday = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")[today.weekday()]
        email = self.ctx.email
        who = "гость" if email.startswith("guest@") else email
        return f"{weekday}, {today.day} {months[today.month - 1]} · {who}"

    def _restore_focus(self) -> None:
        if self.ctx.user_id:
            row = self.ctx.store.latest_usage(self.ctx.user_id)
            if row is not None:
                self.focus.update_focus(row["process"], row["title"] or "")
                return
        self.focus.window_title.setText("Данные появятся через несколько секунд после старта трекинга")

    def _sync_pause_button(self) -> None:
        paused = bool(self.ctx.settings.get("tracking_paused", False))
        self.pause_button.setText("Продолжить" if paused else "Пауза")
        self.pause_button.setObjectName("Primary" if paused else "")
        self.pause_button.style().unpolish(self.pause_button)
        self.pause_button.style().polish(self.pause_button)
        self.status_pill.set_active(not paused)

    def _toggle_pause(self) -> None:
        paused = not bool(self.ctx.settings.get("tracking_paused", False))
        self.ctx.set_tracking_paused(paused)
        self.ctx.toast.emit(
            "Трекинг приостановлен" if paused else "Трекинг снова включён",
            "warn" if paused else "ok",
        )
        self._sync_pause_button()

    def _on_status(self, active: bool) -> None:
        self.status_pill.set_active(active)
        self._sync_pause_button()

    def _on_idle(self, idle: bool) -> None:
        if idle:
            self.status_pill.set_active(False, "Пользователь неактивен")
        else:
            self.status_pill.set_active(not self.ctx.settings.get("tracking_paused", False))

    def _on_usage(self, process: str, title: str) -> None:
        self.status_pill.set_active(True)
        self.focus.update_focus(process, title)

    def _on_capture(self, kind: str, text: str, path: str) -> None:
        self._render_clips()
        self.card_clips.set_value(str(self.ctx.store.clip_count(self.ctx.user_id)))

    # -------------------------------------------------------------- refresh
    def refresh(self) -> None:
        if not self.ctx.user_id:
            return
        today = date.today()
        start_today = int(datetime.combine(today, datetime.min.time()).timestamp())
        now = int(datetime.now().timestamp())

        today_seconds = self.ctx.store.total_seconds(self.ctx.user_id, start_today, now)
        self.card_time.set_value(format_duration(today_seconds, compact=True))
        self.card_clips.set_value(str(self.ctx.store.clip_count(self.ctx.user_id)))
        self.card_apps.set_value(str(self.ctx.store.distinct_apps(self.ctx.user_id, start_today, now)))

        week_start = today - timedelta(days=6)
        totals = self.ctx.store.daily_totals(self.ctx.user_id, week_start, today)
        values = [int(totals.get((week_start + timedelta(days=i)).isoformat(), 0)) for i in range(7)]
        labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        display = [("Сегодня" if week_start + timedelta(days=i) == today else labels[(week_start + timedelta(days=i)).weekday()]) for i in range(7)]
        self.week_chart.set_data(display, values)
        week_total = sum(values)
        average = week_total // 7
        self.card_avg.set_value(
            format_duration(week_total, compact=True) if week_total else "0 мин",
            f"в среднем {format_duration(average, compact=True)} в день",
        )

        self.top_host = self._fill_top_apps(start_today, now)
        self._render_clips()
        self.focus.refresh_time()

    def _fill_top_apps(self, start: int, end: int) -> QVBoxLayout:
        while self.top_host.count():
            item = self.top_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        apps = self.ctx.store.top_apps(self.ctx.user_id, start, end, 5)
        if not apps:
            self.top_host.addWidget(EmptyState("apps", "Пока нет данных", "Откройте любое окно — статистика появится"))
            return self.top_host
        peak = max(a.seconds for a in apps)
        for idx, app in enumerate(apps):
            self.top_host.addWidget(AppUsageRow(app.process, app.seconds, peak, index=idx))
        return self.top_host

    def _render_clips(self) -> None:
        while self.clips_host.count():
            item = self.clips_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        entries = self.ctx.store.clips(self.ctx.user_id, limit=4) if self.ctx.user_id else []
        if not entries:
            self.clips_host.addWidget(
                EmptyState("clipboard", "Буфер пуст", "Скопируйте любой текст — он появится здесь")
            )
            return
        for entry in entries:
            row = ClipRow(entry)
            row.copy_requested.connect(self._copy_entry)
            self.clips_host.addWidget(row)

    def _copy_entry(self, entry) -> None:
        if entry.kind == "image":
            ok = self.ctx.watcher.copy_image_file(entry.image_path)
            self.ctx.toast.emit("Картинка скопирована" if ok else "Не удалось открыть изображение", "ok" if ok else "error")
        else:
            self.ctx.watcher.copy_text(entry.content)
            self.ctx.toast.emit("Скопировано в буфер обмена", "ok")
