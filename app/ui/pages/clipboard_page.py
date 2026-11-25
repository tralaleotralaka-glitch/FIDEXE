"""Full clipboard history with search, filters and quick actions."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...context import AppContext
from ...core.exporter import export_clipboard_csv
from ...core.formatting import plural_ru
from .. import theme
from ..components import ClipRow
from ..widgets import Card, EmptyState, SearchField, SegmentedControl
from .base import Page

MAX_VISIBLE = 150


class ClipboardPage(Page):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(ctx, parent)
        self.p = theme.CURRENT
        self.add_header("Буфер обмена", "0 записей")

        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.clicked.connect(self._export)
        self.add_header_action(self.export_button)

        self.clear_button = QPushButton("Очистить")
        self.clear_button.setObjectName("Danger")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self._clear)
        self.add_header_action(self.clear_button)

        card = Card()
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.search = SearchField("Поиск по содержимому…")
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(self._debounced_refresh)
        toolbar.addWidget(self.search, 1)
        self.filters = SegmentedControl(
            [
                ("all", "Все"),
                ("text", "Текст"),
                ("link", "Ссылки"),
                ("code", "Код"),
                ("image", "Картинки"),
            ],
            "all",
            compact=True,
        )
        self.filters.changed.connect(lambda _: self.refresh())
        toolbar.addWidget(self.filters)
        card.body.addLayout(toolbar)

        self.list_host = QVBoxLayout()
        self.list_host.setSpacing(8)
        card.body.addLayout(self.list_host)
        self.card = card
        self.v.addWidget(card, 1)
        self.v.addStretch(0)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(180)
        self._debounce.timeout.connect(self.refresh)

        ctx.watcher.captured.connect(self._on_capture)

    # ------------------------------------------------------------- helpers
    def _debounced_refresh(self) -> None:
        self._debounce.start()

    def _on_capture(self, *args) -> None:
        if self.isVisible():
            self.refresh()

    def on_show(self) -> None:
        self.refresh()
        self.search.setFocus()

    def refresh(self) -> None:
        user_id = self.ctx.user_id
        total = self.ctx.store.clip_count(user_id) if user_id else 0
        plural = plural_ru(total, "запись", "записи", "записей")
        self.set_subtitle(f"{total} {plural} · всё хранится только на этом компьютере")
        self.clear_button.setEnabled(total > 0)
        self.export_button.setEnabled(total > 0)

        while self.list_host.count():
            item = self.list_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        entries = (
            self.ctx.store.clips(
                user_id,
                query=self.search.text().strip(),
                kind=self.filters.current,
                limit=MAX_VISIBLE,
            )
            if user_id
            else []
        )
        if not entries:
            empty_text = (
                ("Ничего не найдено", "Попробуйте изменить запрос или фильтр")
                if self.search.text().strip() or self.filters.current != "all"
                else ("Буфер пуст", "Скопируйте текст или картинку — запись появится автоматически")
            )
            self.list_host.addWidget(EmptyState("search" if self.search.text().strip() else "clipboard", *empty_text))
            self.list_host.addSpacing(20)
            return

        for entry in entries:
            row = ClipRow(entry, detailed=True)
            row.copy_requested.connect(self._copy)
            row.delete_requested.connect(self._delete)
            row.pin_requested.connect(self._pin)
            row.activated.connect(self._copy)
            self.list_host.addWidget(row)

        if total > MAX_VISIBLE:
            hint = QLabel(f"Показаны последние {MAX_VISIBLE} из {total}. Уточните поиск, чтобы найти остальные.")
            hint.setObjectName("Faint")
            hint.setAlignment(Qt.AlignCenter)
            self.list_host.addWidget(hint)

    # ------------------------------------------------------------- actions
    def _copy(self, entry) -> None:
        if entry.kind == "image":
            ok = self.ctx.watcher.copy_image_file(entry.image_path)
            self.ctx.toast.emit("Картинка скопирована" if ok else "Файл изображения не найден", "ok" if ok else "error")
        else:
            self.ctx.watcher.copy_text(entry.content)
            self.ctx.toast.emit("Скопировано в буфер обмена", "ok")

    def _delete(self, entry) -> None:
        self.ctx.store.delete_clip(entry.id)
        self.refresh()

    def _pin(self, entry) -> None:
        self.ctx.store.set_pinned(entry.id, not entry.pinned)
        self.refresh()

    def _clear(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Очистить историю")
        box.setText("Удалить все записи буфера обмена?")
        box.setInformativeText("Закреплённые записи останутся. Действие нельзя отменить.")
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.button(QMessageBox.Yes).setText("Удалить")
        box.button(QMessageBox.Cancel).setText("Отмена")
        if box.exec() != QMessageBox.Yes:
            return
        removed = self.ctx.store.clear_clips(self.ctx.user_id, keep_pinned=True)
        self.ctx.toast.emit(f"Удалено записей: {removed}", "ok")
        self.refresh()

    def _export(self) -> None:
        from datetime import datetime

        default = f"fidexe_clipboard_{datetime.now():%Y%m%d_%H%M}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт буфера обмена", default, "CSV (*.csv)")
        if not path:
            return
        try:
            from pathlib import Path

            count = export_clipboard_csv(self.ctx.store, self.ctx.user_id, Path(path))
            self.ctx.toast.emit(f"Экспортировано записей: {count}", "ok")
        except OSError as exc:
            self.ctx.toast.emit(f"Не удалось сохранить файл: {exc}", "error")
