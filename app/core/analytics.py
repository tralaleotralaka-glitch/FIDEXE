"""Period helpers and aggregate series for the statistics screens."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .db import AppSlice, Storage

PERIODS = {
    "today": "Сегодня",
    "week": "7 дней",
    "month": "30 дней",
}

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


@dataclass(slots=True)
class DayPoint:
    day: date
    label: str
    seconds: int


@dataclass(slots=True)
class Overview:
    period: str
    start: date
    end: date
    total: int
    days: list[DayPoint]
    top_apps: list[AppSlice]
    hourly: list[int]
    active_days: int
    titles: list[tuple[str, int]]

    @property
    def average(self) -> int:
        counted = max(1, self.active_days)
        return self.total // counted

    @property
    def busiest(self) -> DayPoint | None:
        return max(self.days, key=lambda d: d.seconds) if self.days else None


def period_bounds(period: str, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if period == "today":
        return today, today
    if period == "month":
        return today - timedelta(days=29), today
    return today - timedelta(days=6), today


def _day_label(day: date, today: date) -> str:
    if day == today:
        return "Сегодня"
    if day == today - timedelta(days=1):
        return "Вчера"
    return WEEKDAYS[day.weekday()]


def build_overview(store: Storage, user_id: int, period: str = "week") -> Overview:
    today = date.today()
    start, end = period_bounds(period, today)
    start_ts = int(datetime.combine(start, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(end, datetime.max.time()).timestamp())

    totals = store.daily_totals(user_id, start, end)
    days: list[DayPoint] = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        label = _day_label(cursor, today)
        if period == "month" and label == WEEKDAYS[cursor.weekday()]:
            label = f"{cursor.day:02d}.{cursor.month:02d}" if cursor.day <= 2 else WEEKDAYS[cursor.weekday()]
        days.append(DayPoint(cursor, label, int(totals.get(key, 0))))
        cursor += timedelta(days=1)

    return Overview(
        period=period,
        start=start,
        end=end,
        total=sum(d.seconds for d in days),
        days=days,
        top_apps=store.top_apps(user_id, start_ts, end_ts, 8),
        hourly=store.hourly(user_id, end if period == "today" else today),
        active_days=store.active_days(user_id, start_ts, end_ts),
        titles=store.app_titles(user_id, start_ts, end_ts, 5),
    )


def trend_percent(current: int, previous: int) -> float | None:
    if previous <= 0:
        return None
    return (current - previous) / previous * 100.0
