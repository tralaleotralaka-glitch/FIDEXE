"""Hand painted charts: no QtCharts / matplotlib dependency."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..core.formatting import format_duration
from . import theme

SERIES_COLORS = ("accent", "mint", "blue", "warn", "danger")


def _nice_max(value: float) -> float:
    if value <= 0:
        return 3600.0
    step = 10 ** int(math.floor(math.log10(value)))
    for factor in (1, 1.5, 2, 3, 4, 5, 6, 8, 10):
        candidate = step * factor
        if candidate >= value:
            return candidate
    return step * 10


class _ChartBase(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(150)
        self._hover = -1

    def _font(self, size: int = 10, bold: bool = False) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(size)
        font.setBold(bold)
        return font


class BarChart(_ChartBase):
    """Vertical bars with rounded caps and a hover tooltip."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.labels: list[str] = []
        self.values: list[int] = []
        self.hint: list[str] = []
        self.accent_key = "accent"
        self.setMinimumHeight(180)

    def set_data(self, labels: list[str], values: list[int], hint: list[str] | None = None) -> None:
        self.labels = labels
        self.values = values
        self.hint = hint or [format_duration(v) for v in values]
        self.update()

    def _layout(self) -> tuple[QRectF, float, float]:
        left, right, top, bottom = 4.0, 4.0, 26.0, 26.0
        area = QRectF(left, top, max(10.0, self.width() - left - right), max(10.0, self.height() - top - bottom))
        count = max(1, len(self.values))
        slot = area.width() / count
        return area, slot, min(30.0, slot * 0.56)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        area, slot, _ = self._layout()
        if not self.values or not area.contains(event.position()):
            if self._hover != -1:
                self._hover = -1
                self.update()
            return
        index = int((event.position().x() - area.left()) // slot)
        index = max(0, min(len(self.values) - 1, index))
        if index != self._hover:
            self._hover = index
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = self.p
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area, slot, bar_w = self._layout()
        if not self.values:
            return
        peak = _nice_max(max(self.values) or 3600)

        # grid
        grid_pen = QPen(QColor(p["grid"]), 1, Qt.DashLine)
        grid_pen.setDashPattern([3, 5])
        painter.setFont(self._font(9))
        for step in range(1, 4):
            y = area.bottom() - area.height() * step / 3
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
        if any(self.values):
            painter.setPen(QColor(p["faint"]))
            painter.drawText(
                QRectF(area.left(), area.top() - 20, area.width(), 16),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"макс. {format_duration(peak)}",
            )

        accent = QColor(p[self.accent_key])
        for idx, value in enumerate(self.values):
            cx = area.left() + slot * (idx + 0.5)
            height = 0.0 if peak <= 0 else area.height() * (value / peak)
            height = max(height, 2.0 if value else 0.0)
            rect = QRectF(cx - bar_w / 2, area.bottom() - height, bar_w, height)
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            base = QColor(accent)
            is_hover = idx == self._hover
            gradient.setColorAt(0, base.lighter(115) if is_hover else base)
            tail = QColor(base)
            tail.setAlpha(90 if p["is_dark"] else 120)
            gradient.setColorAt(1, tail)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient if value else QColor(p["card_alt"]))
            painter.drawRoundedRect(rect if value else QRectF(rect.x(), area.bottom() - 3, rect.width(), 3), 6, 6)

            painter.setPen(QColor(p["text"] if is_hover else p["muted"]))
            painter.setFont(self._font(9, bold=is_hover))
            label = self.labels[idx] if idx < len(self.labels) else ""
            painter.drawText(
                QRectF(cx - slot / 2, area.bottom() + 6, slot, 16),
                Qt.AlignHCenter | Qt.AlignTop,
                label,
            )

        if self._hover >= 0:
            self._draw_tooltip(painter, area, slot, bar_w)

    def _draw_tooltip(self, painter: QPainter, area: QRectF, slot: float, bar_w: float) -> None:
        p = self.p
        idx = self._hover
        if idx >= len(self.values):
            return
        text = f"{self.labels[idx]} · {self.hint[idx]}" if idx < len(self.hint) else str(self.values[idx])
        metrics = QFontMetrics(self._font(10, bold=True))
        w = metrics.horizontalAdvance(text) + 20
        h = 24.0
        cx = area.left() + slot * (idx + 0.5)
        x = min(max(area.left(), cx - w / 2), area.right() - w)
        y = max(0.0, area.top() - 10)
        box = QRectF(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["card_hover"]))
        painter.drawRoundedRect(box, 7, 7)
        painter.setFont(self._font(10, bold=True))
        painter.setPen(QColor(p["text"]))
        painter.drawText(box, Qt.AlignCenter, text)


class AreaChart(_ChartBase):
    """Smooth area chart used for the hourly rhythm of the day."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.values: list[int] = []
        self.labels: list[str] = []
        self.accent_key = "mint"
        self.setMinimumHeight(170)

    def set_data(self, labels: list[str], values: list[int]) -> None:
        self.labels = labels
        self.values = values
        self.update()

    def _area(self) -> QRectF:
        return QRectF(8, 14, max(10.0, self.width() - 16), max(10.0, self.height() - 40))

    def _points(self) -> list[QPointF]:
        area = self._area()
        count = max(1, len(self.values) - 1)
        peak = _nice_max(max(self.values) if self.values else 0)
        return [
            QPointF(area.left() + area.width() * i / count, area.bottom() - area.height() * (v / peak))
            for i, v in enumerate(self.values)
        ]

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        area = self._area()
        if not self.values or not area.contains(event.position()):
            if self._hover != -1:
                self._hover = -1
                self.update()
            return
        step = area.width() / max(1, len(self.values) - 1)
        idx = round((event.position().x() - area.left()) / step)
        idx = max(0, min(len(self.values) - 1, idx))
        if idx != self._hover:
            self._hover = idx
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = self.p
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self._area()
        if len(self.values) < 2:
            return
        points = self._points()

        path = QPainterPath(points[0])
        for i in range(1, len(points)):
            prev = points[i - 1]
            cur = points[i]
            mid_x = (prev.x() + cur.x()) / 2
            path.cubicTo(QPointF(mid_x, prev.y()), QPointF(mid_x, cur.y()), cur)

        fill = QPainterPath(path)
        fill.lineTo(points[-1].x(), area.bottom())
        fill.lineTo(points[0].x(), area.bottom())
        fill.closeSubpath()

        base = QColor(p[self.accent_key])
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        top_color = QColor(base)
        top_color.setAlpha(110 if p["is_dark"] else 90)
        bottom_color = QColor(base)
        bottom_color.setAlpha(0)
        gradient.setColorAt(0, top_color)
        gradient.setColorAt(1, bottom_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(fill)

        pen = QPen(base, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        for step in range(0, 24, 6):
            if step >= len(self.labels):
                break
            x = area.left() + area.width() * step / max(1, len(self.values) - 1)
            painter.setPen(QColor(p["faint"]))
            painter.setFont(self._font(9))
            painter.drawText(QRectF(x - 16, area.bottom() + 8, 32, 16), Qt.AlignHCenter, self.labels[step])

        if 0 <= self._hover < len(points):
            point = points[self._hover]
            painter.setPen(QPen(QColor(p["card"]), 2))
            painter.setBrush(base)
            painter.drawEllipse(point, 5, 5)
            text = f"{self.labels[self._hover]} · {format_duration(self.values[self._hover])}"
            metrics = QFontMetrics(self._font(10, bold=True))
            w = metrics.horizontalAdvance(text) + 18
            box = QRectF(
                min(max(area.left(), point.x() - w / 2), area.right() - w),
                max(0.0, point.y() - 34),
                w,
                22,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(p["card_hover"]))
            painter.drawRoundedRect(box, 6, 6)
            painter.setPen(QColor(p["text"]))
            painter.setFont(self._font(10, bold=True))
            painter.drawText(box, Qt.AlignCenter, text)


class DonutChart(_ChartBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.slices: list[tuple[str, int]] = []
        self.center_title = ""
        self.center_caption = ""
        self.setMinimumHeight(190)
        self.setMinimumWidth(190)

    def set_data(
        self,
        slices: list[tuple[str, int]],
        center_title: str = "",
        center_caption: str = "",
    ) -> None:
        self.slices = [(label, value) for label, value in slices if value > 0]
        self.center_title = center_title
        self.center_caption = center_caption
        self.update()

    def _geometry(self) -> tuple[QRectF, float]:
        size = min(self.width(), self.height()) - 16
        rect = QRectF((self.width() - size) / 2, (self.height() - size) / 2, size, size)
        thickness = max(12.0, size * 0.13)
        return rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2), thickness

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        rect, _ = self._geometry()
        center = rect.center()
        dx = event.position().x() - center.x()
        dy = event.position().y() - center.y()
        radius = math.hypot(dx, dy)
        if not self.slices or radius < rect.width() / 2 - 24 or radius > rect.width() / 2 + 24:
            if self._hover != -1:
                self._hover = -1
                self.update()
            return
        angle = (math.degrees(math.atan2(-dy, dx))) % 360
        start = 90.0
        total = sum(v for _, v in self.slices) or 1
        hover = -1
        for idx, (_, value) in enumerate(self.slices):
            span = value / total * 360.0
            begin = (start - span) % 360
            if span >= 359.9 or (angle >= begin and angle <= begin + span):
                hover = idx
                break
            start = begin
        if hover != self._hover:
            self._hover = hover
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = self.p
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect, thickness = self._geometry()
        total = sum(v for _, v in self.slices)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["card_alt"]))
        painter.drawEllipse(rect.adjusted(-thickness / 2, -thickness / 2, thickness / 2, thickness / 2).adjusted(-1, -1, 1, 1))

        if total <= 0:
            pass
        else:
            start_angle = 90 * 16
            for idx, (_, value) in enumerate(self.slices):
                span = -int(round(value / total * 360 * 16))
                color_key = SERIES_COLORS[idx % len(SERIES_COLORS)]
                color = QColor(p[color_key])
                if idx == self._hover:
                    color = color.lighter(112)
                pen = QPen(color, thickness, Qt.SolidLine, Qt.FlatCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                arc_rect = rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2)
                painter.drawArc(arc_rect, start_angle, span - (0 if span == -int(round(360 * 16)) else 0))
                start_angle += span

        inner = rect.adjusted(thickness, thickness, -thickness, -thickness)
        painter.setPen(QColor(p["text"]))
        font = self._font(max(15, int(inner.height() * 0.16)), bold=True)
        painter.setFont(font)
        caption_rect = QRectF(inner.left(), inner.center().y() - inner.height() * 0.10, inner.width(), inner.height() * 0.3)
        title_rect = QRectF(inner.left(), inner.center().y() - inner.height() * 0.42, inner.width(), inner.height() * 0.4)
        painter.drawText(title_rect, Qt.AlignCenter, self.center_title)
        painter.setFont(self._font(10))
        painter.setPen(QColor(p["muted"]))
        painter.drawText(caption_rect, Qt.AlignHCenter | Qt.AlignTop, self.center_caption)


class Sparkline(_ChartBase):
    """Tiny trend line for cards."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.values: list[int] = []
        self.accent_key = "accent"
        self.setMinimumHeight(44)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def set_data(self, values: list[int]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if len(self.values) < 2:
            return
        p = self.p
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = QRectF(2, 2, max(4.0, self.width() - 4), max(4.0, self.height() - 4))
        peak = max(self.values) or 1
        points = [
            QPointF(area.left() + area.width() * i / (len(self.values) - 1),
                    area.bottom() - area.height() * (v / peak) * 0.9)
            for i, v in enumerate(self.values)
        ]
        fill = QPainterPath(points[0])
        for i in range(1, len(points)):
            prev, cur = points[i - 1], points[i]
            mid_x = (prev.x() + cur.x()) / 2
            fill.cubicTo(QPointF(mid_x, prev.y()), QPointF(mid_x, cur.y()), cur)
        line = QPainterPath(fill)
        fill.lineTo(points[-1].x(), area.bottom())
        fill.lineTo(points[0].x(), area.bottom())
        fill.closeSubpath()

        base = QColor(p[self.accent_key])
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        top_color = QColor(base)
        top_color.setAlpha(70)
        bottom_color = QColor(base)
        bottom_color.setAlpha(0)
        gradient.setColorAt(0, top_color)
        gradient.setColorAt(1, bottom_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(fill)
        pen = QPen(base, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line)
