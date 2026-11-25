"""Composite rows shared by several pages."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.db import ClipEntry
from ..core.formatting import (
    app_initials,
    app_label,
    format_duration,
    relative_time,
    short_title,
)
from . import icons, theme
from .widgets import ElidedLabel, IconButton


class AppBadge(QWidget):
    """Rounded gradient tile with the application initials."""

    def __init__(self, text: str, size: int = 34, color_key: str = "accent", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.text = text.upper()[:2]
        self._size = size
        self.color_key = color_key
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.p[self.color_key])
        soft = QColor(color)
        soft.setAlpha(38 if self.p["is_dark"] else 26)
        painter.setPen(Qt.NoPen)
        painter.setBrush(soft)
        painter.drawRoundedRect(QRectF(0, 0, self._size, self._size), self._size * 0.3, self._size * 0.3)
        font = QFont(self.font())
        font.setPixelSize(max(10, int(self._size * 0.34)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(QRectF(0, 0, self._size, self._size), Qt.AlignCenter, self.text)


class ProgressBar(QWidget):
    def __init__(self, value: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.value = max(0.0, min(1.0, value))
        self.color_key = "accent"
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: float, color_key: str | None = None) -> None:
        self.value = max(0.0, min(1.0, value))
        if color_key:
            self.color_key = color_key
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.p["card_alt"]))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), 6), 3, 3)
        if self.value > 0:
            painter.setBrush(QColor(self.p[self.color_key]))
            painter.drawRoundedRect(QRectF(0, 0, max(6.0, self.width() * self.value), 6), 3, 3)


class AppUsageRow(QWidget):
    def __init__(
        self,
        process: str,
        seconds: int,
        peak: int,
        color_keys: tuple[str, ...] = ("accent", "mint", "blue", "warn", "danger"),
        index: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        color_key = color_keys[index % len(color_keys)]
        layout.addWidget(AppBadge(app_initials(process), 32, color_key), 0, Qt.AlignVCenter)

        middle = QVBoxLayout()
        middle.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(6)
        name = QLabel(app_label(process))
        name.setStyleSheet("font-size: 12.5px; font-weight: 600;")
        top.addWidget(name)
        top.addStretch(1)
        value = QLabel(format_duration(seconds, compact=True))
        value.setObjectName("Subtitle")
        top.addWidget(value)
        middle.addLayout(top)
        bar = ProgressBar(seconds / peak if peak else 0.0)
        bar.set_value(seconds / peak if peak else 0.0, color_key)
        middle.addWidget(bar)
        layout.addLayout(middle, 1)


class LegendRow(QWidget):
    def __init__(self, color_key: str, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(f"background: {self.p[color_key]}; border-radius: 4px;")
        layout.addWidget(dot, 0, Qt.AlignVCenter)
        self.name = QLabel(label)
        self.name.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.name)
        layout.addStretch(1)
        self.value = QLabel(value)
        self.value.setObjectName("Subtitle")
        layout.addWidget(self.value)


class SettingsRow(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        control: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(14)
        text_block = QVBoxLayout()
        text_block.setSpacing(2)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 12.5px; font-weight: 600;")
        text_block.addWidget(self.title)
        if subtitle:
            self.subtitle = QLabel(subtitle)
            self.subtitle.setObjectName("Subtitle")
            self.subtitle.setWordWrap(True)
            text_block.addWidget(self.subtitle)
        layout.addLayout(text_block, 1)
        if control is not None:
            layout.addWidget(control, 0, Qt.AlignVCenter)


class ClipRow(QFrame):
    """Compact clipboard entry used on the dashboard and in the full list."""

    activated = Signal(object)
    copy_requested = Signal(object)
    delete_requested = Signal(object)
    pin_requested = Signal(object)

    def __init__(
        self,
        entry: ClipEntry,
        *,
        detailed: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.entry = entry
        self.detailed = detailed
        self.setObjectName("InnerCard" if detailed else "")
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12 if detailed else 2, 10 if detailed else 6, 10 if detailed else 2, 10 if detailed else 6)
        layout.setSpacing(11)

        self.thumb: QLabel | None = None
        if entry.kind == "image" and entry.image_path:
            self.thumb = QLabel()
            self.thumb.setFixedSize(46, 46)
            pix = icons.pixmap("image", self.p["blue"], 18)
            self.thumb.setPixmap(pix)
            self.thumb.setAlignment(Qt.AlignCenter)
            self.thumb.setStyleSheet(f"background: {self.p['card_alt']}; border-radius: 10px;")
            layout.addWidget(self.thumb, 0, Qt.AlignTop)
        else:
            color_key = {"link": "blue", "code": "warn", "text": "accent"}.get(entry.kind, "accent")
            icon_name = {"link": "link", "code": "code", "text": "text"}.get(entry.kind, "text")
            badge = QLabel()
            badge.setFixedSize(34, 34)
            badge.setPixmap(icons.pixmap(icon_name, self.p[color_key], 15))
            badge.setAlignment(Qt.AlignCenter)
            soft = self.p.get(f"{color_key}_soft") or self.p["accent_soft"]
            badge.setStyleSheet(f"background: {soft}; border-radius: 10px;")
            layout.addWidget(badge, 0, Qt.AlignTop)

        text_block = QVBoxLayout()
        text_block.setSpacing(3)
        preview = (
            "Изображение из буфера обмена"
            if entry.kind == "image"
            else short_title(entry.content, limit=400 if detailed else 220)
        )
        label_class = QLabel if detailed else ElidedLabel
        self.body_label = label_class(preview or "Пустая запись")
        if detailed:
            self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.body_label.setStyleSheet(
            "font-size: 12.5px;"
            + ("font-family: 'Cascadia Mono','Consolas','DejaVu Sans Mono',monospace; font-size: 11.5px;"
               if entry.kind == "code" and detailed else "")
        )
        text_block.addWidget(self.body_label)
        self.setMinimumHeight(64 if detailed else 46)

        meta_bits = [self._kind_label(entry.kind), relative_time(entry.created_at)]
        if entry.pinned:
            meta_bits.append("закреплено")
        meta = QLabel(" · ".join(meta_bits))
        meta.setObjectName("Faint")
        text_block.addWidget(meta)
        layout.addLayout(text_block, 1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(2)
        if entry.pinned:
            pin = IconButton("pin", "Открепить", self.p["accent"], 15)
        else:
            pin = IconButton("pin", "Закрепить", self.p["faint"], 15)
        pin.clicked.connect(lambda: self.pin_requested.emit(entry))
        copy = IconButton("copy", "Скопировать", self.p["muted"], 15)
        copy.clicked.connect(lambda: self.copy_requested.emit(entry))
        self.actions.addWidget(pin)
        self.actions.addWidget(copy)
        if detailed:
            delete = IconButton("trash", "Удалить", self.p["muted"], 15)
            delete.clicked.connect(lambda: self.delete_requested.emit(entry))
            self.actions.addWidget(delete)
        layout.addLayout(self.actions, 0)

    @staticmethod
    def _kind_label(kind: str) -> str:
        return {"text": "текст", "link": "ссылка", "code": "код", "image": "картинка"}.get(kind, kind)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.activated.emit(self.entry)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        if self.detailed:
            self.setStyleSheet(
                f"#InnerCard {{ background: {self.p['card_hover']}; border: 1px solid {self.p['border']}; border-radius: 12px; }}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.detailed:
            self.setStyleSheet("")
        super().leaveEvent(event)
