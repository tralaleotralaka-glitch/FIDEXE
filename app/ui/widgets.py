"""Reusable presentation widgets."""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme


class Card(QFrame):
    """Rounded panel with an optional header row."""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setObjectName("Card")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(18, 16, 18, 18)
        self._outer.setSpacing(12)

        self.header: QHBoxLayout | None = None
        self.actions: QHBoxLayout | None = None
        if title or subtitle:
            self.header = QHBoxLayout()
            self.header.setSpacing(10)
            if icon_name:
                badge = QLabel()
                badge.setPixmap(icons.pixmap(icon_name, self.p["accent"], 16))
                badge.setFixedSize(28, 28)
                badge.setAlignment(Qt.AlignCenter)
                badge.setStyleSheet(
                    f"background: {self.p['accent_soft']}; border-radius: 9px;"
                )
                self.header.addWidget(badge, 0, Qt.AlignVCenter)
            text_block = QVBoxLayout()
            text_block.setSpacing(1)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            text_block.addWidget(self.title_label)
            if subtitle:
                self.subtitle_label = QLabel(subtitle)
                self.subtitle_label.setObjectName("Subtitle")
                text_block.addWidget(self.subtitle_label)
            self.header.addLayout(text_block)
            self.header.addStretch(1)
            self.actions = QHBoxLayout()
            self.actions.setSpacing(6)
            self.header.addLayout(self.actions)
            self._outer.addLayout(self.header)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self._outer.addLayout(self.body, 1)

    def add_action(self, widget: QWidget) -> QWidget:
        if self.actions is not None:
            self.actions.addWidget(widget, 0, Qt.AlignVCenter)
        return widget

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self.body.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout, stretch: int = 0):
        self.body.addLayout(layout, stretch)
        return layout


class StatCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "—",
        hint: str = "",
        icon_name: str = "clock",
        accent: str = "accent",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.accent_key = accent
        self._icon_name = icon_name
        self.setObjectName("Card")
        self.setMinimumHeight(106)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.badge = QLabel()
        self.badge.setFixedSize(30, 30)
        self.badge.setAlignment(Qt.AlignCenter)
        top.addWidget(self.badge, 0, Qt.AlignTop)
        top.addStretch(1)
        self.trend = QLabel("")
        self.trend.setObjectName("BadgeAccent")
        self.trend.setVisible(False)
        top.addWidget(self.trend, 0, Qt.AlignTop)
        layout.addLayout(top)

        self.caption = QLabel(title)
        self.caption.setObjectName("Subtitle")
        layout.addWidget(self.caption)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        layout.addWidget(self.value_label)

        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("Faint")
        self.hint_label.setVisible(bool(hint))
        layout.addWidget(self.hint_label)
        layout.addStretch(1)

        self._style_badge()

    def _style_badge(self) -> None:
        color = self.p[self.accent_key]
        soft = self.p.get(f"{self.accent_key}_soft") or self.p["accent_soft"]
        self.badge.setStyleSheet(f"background: {soft}; border-radius: 10px;")
        self.badge.setPixmap(icons.pixmap(self._icon_name, color, 16))

    def set_icon(self, name: str, accent: str | None = None) -> None:
        self._icon_name = name
        if accent:
            self.accent_key = accent
        self._style_badge()

    def set_value(self, value: str, hint: str = "", trend: float | None = None) -> None:
        self.value_label.setText(value)
        if hint:
            self.hint_label.setText(hint)
            self.hint_label.setVisible(True)
        if trend is None:
            self.trend.setVisible(False)
        else:
            arrow = "↑" if trend >= 0 else "↓"
            color = self.p["mint"] if trend >= 0 else self.p["danger"]
            soft = self.p["mint_soft"] if trend >= 0 else self.p["danger_soft"]
            self.trend.setText(f"{arrow} {abs(trend):.0f}%")
            self.trend.setStyleSheet(
                f"background: {soft}; color: {color}; border-radius: 9px; padding: 3px 8px;"
                "font-size: 10px; font-weight: 700;"
            )
            self.trend.setVisible(True)


class ElidedLabel(QLabel):
    """Single line label that shortens text with an ellipsis instead of wrapping."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text
        super().setText(text)
        self.update()

    def full_text(self) -> str:
        return self._full

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        text = metrics.elidedText(self._full, Qt.ElideRight, max(10, self.width()))
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), int(self.alignment()), text)


class IconButton(QPushButton):
    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        color: str | None = None,
        size: int = 18,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.icon_name = icon_name
        self.color = color or self.p["muted"]
        self.setObjectName("IconButton")
        self.setIcon(icons.icon(icon_name, self.color, size))
        self.setIconSize(QSize(size, size))
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size + 14, size + 14)
        if tooltip:
            self.setToolTip(tooltip)

    def set_color(self, color: str) -> None:
        self.color = color
        self.setIcon(icons.icon(self.icon_name, color, self.iconSize().width()))


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._ratio = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"ratio", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.toggled.connect(self._animate)

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._ratio)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def get_ratio(self) -> float:
        return self._ratio

    def set_ratio(self, value: float) -> None:
        self._ratio = value
        self.update()

    ratio = Property(float, get_ratio, set_ratio)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(0, 2, 44, 20)
        off = QColor(self.p["card_hover"])
        on = QColor(self.p["accent"])
        r = self._ratio
        color = QColor(
            int(off.red() + (on.red() - off.red()) * r),
            int(off.green() + (on.green() - off.green()) * r),
            int(off.blue() + (on.blue() - off.blue()) * r),
        )
        painter.setPen(QPen(QColor(self.p["border"]), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(track, 10, 10)
        knob_x = 3 + r * 20
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(knob_x, 4, 16, 16))


class Avatar(QWidget):
    def __init__(self, text: str, size: int = 36, accent: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.text = text.upper()[:2]
        self.accent = accent or self.p["accent"]
        self.setFixedSize(size, size)
        self._size = size

    def set_text(self, text: str) -> None:
        self.text = text.upper()[:2]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self._size, self._size)
        grad.setColorAt(0, QColor(self.accent))
        grad.setColorAt(1, QColor(self.p["mint"] if self.accent == self.p["accent"] else self.p["blue"]))
        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(QRectF(0, 0, self._size, self._size))
        font = QFont(self.font())
        font.setPixelSize(max(11, int(self._size * 0.36)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, 0, self._size, self._size), Qt.AlignCenter, self.text)


class SegmentedControl(QWidget):
    """Pill style tab switcher drawn by hand for a consistent look."""

    changed = Signal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        current: str = "",
        *,
        compact: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.options = options
        self.current = current or (options[0][0] if options else "")
        self.compact = compact
        self._hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def _font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(12 if not self.compact else 11)
        font.setBold(True)
        return font

    def _padding(self) -> int:
        return 12 if not self.compact else 9

    def sizeHint(self) -> QSize:  # noqa: N802
        metrics = QFontMetrics(self._font())
        width = sum(metrics.horizontalAdvance(label) + self._padding() * 2 for _, label in self.options) + 8
        return QSize(width, 34 if not self.compact else 28)

    def _rects(self) -> list[QRectF]:
        metrics = QFontMetrics(self._font())
        pad = self._padding()
        rects: list[QRectF] = []
        x = 4.0
        height = 34 if not self.compact else 28
        for _, label in self.options:
            w = metrics.horizontalAdvance(label) + pad * 2
            rects.append(QRectF(x, 4, w, height - 8))
            x += w
        return rects

    def set_current(self, key: str, *, emit: bool = False) -> None:
        if key == self.current:
            return
        self.current = key
        self.update()
        if emit:
            self.changed.emit(key)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        hover = -1
        for idx, rect in enumerate(self._rects()):
            if rect.contains(pos):
                hover = idx
                break
        if hover != self._hover:
            self._hover = hover
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = -1
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        for idx, rect in enumerate(self._rects()):
            if rect.contains(event.position()):
                key = self.options[idx][0]
                if key != self.current:
                    self.current = key
                    self.update()
                    self.changed.emit(key)
                return

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(self.p["border_soft"]), 1))
        painter.setBrush(QColor(self.p["card_alt"]))
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 11, 11)

        rects = self._rects()
        for idx, rect in enumerate(rects):
            key, label = self.options[idx]
            if key == self.current:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(self.p["accent"]))
                painter.drawRoundedRect(rect, 8, 8)
                text_color = QColor("#FFFFFF")
            else:
                if idx == self._hover:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(self.p["card_hover"]))
                    painter.drawRoundedRect(rect, 8, 8)
                text_color = QColor(self.p["muted"])
            painter.setPen(text_color)
            painter.setFont(self._font())
            painter.drawText(rect, Qt.AlignCenter, label)


class SidebarButton(QAbstractButton):
    def __init__(self, key: str, label: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.key = key
        self.label = label
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._hover = False

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        active = self.isChecked()
        if active:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.p["accent_soft"]))
            painter.drawRoundedRect(rect, 11, 11)
            painter.setBrush(QColor(self.p["accent"]))
            painter.drawRoundedRect(QRectF(0, 11, 3, 20), 1.5, 1.5)
        elif self._hover:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.p["card_alt"]))
            painter.drawRoundedRect(rect, 11, 11)

        color = self.p["accent"] if active else (self.p["text"] if self._hover else self.p["muted"])
        pm = icons.pixmap(self.icon_name, color, 18)
        painter.drawPixmap(QPointF(14, (self.height() - 18) / 2), pm)

        font = QFont(self.font())
        font.setPixelSize(13)
        font.setBold(active)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(42, 0, self.width() - 50, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.label)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Поиск", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setObjectName("Search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(38)
        self._icon = QLabel(self)
        self._icon.setPixmap(icons.pixmap("search", self.p["muted"], 15))
        self._icon.setFixedSize(18, 18)
        self._icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._icon.move(13, 10)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._icon.move(13, (self.height() - 18) // 2)


class EmptyState(QWidget):
    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addStretch(1)
        badge = QLabel()
        badge.setFixedSize(52, 52)
        badge.setPixmap(icons.pixmap(icon_name, self.p["faint"], 24))
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background: {self.p['card_alt']}; border-radius: 16px;")
        layout.addWidget(badge, 0, Qt.AlignHCenter)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("Subtitle")
            sub.setAlignment(Qt.AlignCenter)
            sub.setWordWrap(True)
            layout.addWidget(sub)
        layout.addStretch(1)


def hline(color_key: str = "border_soft") -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {theme.CURRENT[color_key]}; border: none;")
    return line


def soft_shadow(widget: QWidget, blur: int = 26, alpha: int = 40, offset: int = 6) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
