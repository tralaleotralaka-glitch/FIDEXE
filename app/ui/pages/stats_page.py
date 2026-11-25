"""Statistics page: daily bars, app donut, hourly rhythm and top windows."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...core.analytics import PERIODS, build_overview
from ...core.exporter import export_usage_csv
from ...core.formatting import app_label, format_duration, plural_ru, short_title
from .. import theme
from ..charts import AreaChart, BarChart, DonutChart
from ..components import AppUsageRow, LegendRow
from ..widgets import Card, EmptyState, SegmentedControl, StatCard
from .base import Page

SERIES = ("accent", "mint", "blue", "warn", "danger")


class StatsPage(Page):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(ctx, parent)
        self.p = theme.CURRENT
        self.period = "week"
        self.add_header("Статистика", "Активность приложений по дням и часам")

        self.period_switch = SegmentedControl(
            [(key, label) for key, label in PERIODS.items()], self.period
        )
        self.period_switch.changed.connect(self._on_period)
        self.add_header_action(self.period_switch)

        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.clicked.connect(self._export)
        self.add_header_action(self.export_button)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_total = StatCard("Всего в фокусе", "0 мин", "за выбранный период", "clock", "accent")
        self.card_avg = StatCard("В среднем в день", "0 мин", "", "chart", "mint")
        self.card_days = StatCard("Активных дней", "0", "", "calendar", "blue")
        self.card_top = StatCard("Чаще всего", "—", "", "flame", "warn")
        for card in (self.card_total, self.card_avg, self.card_days, self.card_top):
            cards.addWidget(card, 1)
        self.v.addLayout(cards)

        self.daily_card = Card("Время по дням", "суммарное время в активном окне", "chart")
        self.daily_card.setMinimumHeight(290)
        self.daily_chart = BarChart()
        self.daily_chart.setMinimumHeight(210)
        self.daily_card.add(self.daily_chart, 1)
        self.v.addWidget(self.daily_card)

        row = QHBoxLayout()
        row.setSpacing(14)

        self.donut_card = Card("Распределение по приложениям", "доля времени в фокусе", "apps")
        self.donut_card.setMinimumHeight(300)
        donut_row = QHBoxLayout()
        donut_row.setSpacing(16)
        self.donut = DonutChart()
        self.donut.setMinimumSize(200, 200)
        donut_row.addWidget(self.donut, 0, Qt.AlignTop)
        self.legend_host = QVBoxLayout()
        self.legend_host.setSpacing(3)
        donut_row.addLayout(self.legend_host, 1)
        self.donut_card.body.addLayout(donut_row)
        row.addWidget(self.donut_card, 1)

        self.rhythm_card = Card("Ритм дня", "активность по часам", "clock")
        self.rhythm_card.setMinimumHeight(300)
        self.rhythm = AreaChart()
        self.rhythm.setMinimumHeight(200)
        self.rhythm_card.add(self.rhythm, 1)
        row.addWidget(self.rhythm_card, 1)
        self.v.addLayout(row, 1)

        lists = QHBoxLayout()
        lists.setSpacing(14)
        self.apps_card = Card("Топ приложений", "", "apps")
        self.apps_card.setMinimumHeight(250)
        self.apps_host = QVBoxLayout()
        self.apps_host.setSpacing(2)
        self.apps_card.body.addLayout(self.apps_host)
        self.apps_card.body.addStretch(1)
        lists.addWidget(self.apps_card, 1)

        self.titles_card = Card("Самые долгие окна", "по заголовкам", "text")
        self.titles_card.setMinimumHeight(250)
        self.titles_host = QVBoxLayout()
        self.titles_host.setSpacing(8)
        self.titles_card.body.addLayout(self.titles_host)
        self.titles_card.body.addStretch(1)
        lists.addWidget(self.titles_card, 1)
        self.v.addLayout(lists, 1)
        self.v.addStretch(0)

    # ------------------------------------------------------------- actions
    def _on_period(self, period: str) -> None:
        self.period = period
        self.refresh()

    def _export(self) -> None:
        default = f"fidexe_usage_{datetime.now():%Y%m%d_%H%M}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт статистики", default, "CSV (*.csv)")
        if not path:
            return
        try:
            days = {"today": 1, "week": 7, "month": 30}.get(self.period, 7)
            count = export_usage_csv(self.ctx.store, self.ctx.user_id, Path(path), days=days)
            self.ctx.toast.emit(f"Экспортировано строк: {count}", "ok")
        except OSError as exc:
            self.ctx.toast.emit(f"Не удалось сохранить файл: {exc}", "error")

    # ------------------------------------------------------------- content
    def _clear(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def refresh(self) -> None:
        if not self.ctx.user_id:
            return
        data = build_overview(self.ctx.store, self.ctx.user_id, self.period)

        self.card_total.set_value(format_duration(data.total, compact=True), "активное время за период")
        self.card_avg.set_value(format_duration(data.average, compact=True), "по активным дням")
        plural = plural_ru(data.active_days, "день", "дня", "дней")
        self.card_days.set_value(str(data.active_days), f"{plural} с данными")
        top_name = app_label(data.top_apps[0].process) if data.top_apps else "—"
        self.card_top.set_value(top_name, format_duration(data.top_apps[0].seconds, compact=True) if data.top_apps else "")

        if self.period == "month":
            labels = [f"{d.day:02d}" for d in data.days]
        else:
            labels = [d.label for d in data.days]
        self.daily_chart.set_data(labels, [d.seconds for d in data.days])
        self.daily_card.subtitle_label.setText(
            {"today": "сегодня по часам ниже", "week": "последние 7 дней", "month": "последние 30 дней"}[self.period]
        )

        self._render_donut(data)
        hours = data.hourly
        self.rhythm.set_data([f"{h:02d}:00" for h in range(24)], hours)
        peak_hour = max(range(24), key=lambda h: hours[h]) if any(hours) else None
        self.rhythm_card.subtitle_label.setText(
            f"пик активности в {peak_hour:02d}:00" if peak_hour is not None else "активность по часам"
        )

        self._clear(self.apps_host)
        if data.top_apps:
            peak = max(a.seconds for a in data.top_apps)
            for idx, app in enumerate(data.top_apps):
                self.apps_host.addWidget(AppUsageRow(app.process, app.seconds, peak, index=idx))
        else:
            self.apps_host.addWidget(EmptyState("apps", "Нет данных", "Трекинг включён, но активность ещё не записана"))

        self._clear(self.titles_host)
        if data.titles:
            peak = max(v for _, v in data.titles)
            for title, seconds in data.titles:
                self.titles_host.addWidget(self._title_row(title, seconds, peak))
        else:
            self.titles_host.addWidget(EmptyState("text", "Пока пусто", "Заголовки окон появятся здесь"))

    def _render_donut(self, data) -> None:
        self._clear(self.legend_host)
        top = data.top_apps[:5]
        if not top:
            self.donut.set_data([], "—", "нет данных")
            self.legend_host.addWidget(QLabel("Недостаточно данных"))
            return
        total = sum(a.seconds for a in top) or 1
        self.donut.set_data(
            [(app_label(a.process), a.seconds) for a in top],
            format_duration(data.total, compact=True),
            "всего",
        )
        for idx, app in enumerate(top):
            share = f"{app.seconds / total * 100:.0f}%"
            self.legend_host.addWidget(
                LegendRow(SERIES[idx % len(SERIES)], app_label(app.process), share)
            )
        self.legend_host.addStretch(1)

    def _title_row(self, title: str, seconds: int, peak: int) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(8)
        label = QLabel(short_title(title, limit=58))
        label.setStyleSheet("font-size: 12px;")
        head.addWidget(label, 1)
        value = QLabel(format_duration(seconds, compact=True))
        value.setObjectName("Subtitle")
        head.addWidget(value)
        layout.addLayout(head)
        from ..components import ProgressBar

        bar = ProgressBar(seconds / peak if peak else 0)
        bar.set_value(seconds / peak if peak else 0, "blue")
        layout.addWidget(bar)
        return row
