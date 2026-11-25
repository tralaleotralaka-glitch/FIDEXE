"""Scrollable page base class with a consistent header."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from .. import theme


class Page(QScrollArea):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.p = theme.CURRENT
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background: transparent;")
        self.content = QWidget()
        self.content.setObjectName("PageContent")
        self.v = QVBoxLayout(self.content)
        self.v.setContentsMargins(30, 24, 30, 28)
        self.v.setSpacing(16)
        self.v.setSizeConstraint(QLayout.SetMinimumSize)
        self.setWidget(self.content)
        self._header_actions: QHBoxLayout | None = None

    # ------------------------------------------------------------------ ui
    def add_header(self, title: str, subtitle: str = "") -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        block = QVBoxLayout()
        block.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        block.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("Subtitle")
        block.addWidget(self.subtitle_label)
        row.addLayout(block)
        row.addStretch(1)
        self._header_actions = QHBoxLayout()
        self._header_actions.setSpacing(8)
        row.addLayout(self._header_actions)
        self.v.addLayout(row)
        return self._header_actions

    def add_header_action(self, widget: QWidget) -> QWidget:
        if self._header_actions is not None:
            self._header_actions.addWidget(widget, 0, Qt.AlignVCenter)
        return widget

    def set_subtitle(self, text: str) -> None:
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setText(text)

    # -------------------------------------------------------------- hooks
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        """Reload page data. Overridden by pages."""
