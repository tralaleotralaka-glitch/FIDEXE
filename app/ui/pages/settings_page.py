"""Settings: account, appearance, tracking, clipboard, system and data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...core import autostart, power, remote
from ...core.auth import AuthError
from ...core.exporter import export_json, export_usage_csv
from ...core.paths import APP_TITLE, APP_VERSION, data_dir
from .. import theme
from ..components import SettingsRow
from ..widgets import Avatar, Card, SegmentedControl, ToggleSwitch, hline
from .base import Page


class ChangePasswordDialog(QDialog):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.p = theme.CURRENT
        self.setWindowTitle("Смена пароля")
        self.setFixedWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        title = QLabel("Смена пароля")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        hint = QLabel("Пароль хранится локально в виде хеша PBKDF2-SHA256.")
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.current = QLineEdit()
        self.current.setEchoMode(QLineEdit.Password)
        self.current.setPlaceholderText("Текущий пароль")
        self.new = QLineEdit()
        self.new.setEchoMode(QLineEdit.Password)
        self.new.setPlaceholderText("Новый пароль (минимум 6 символов)")
        self.repeat = QLineEdit()
        self.repeat.setEchoMode(QLineEdit.Password)
        self.repeat.setPlaceholderText("Повторите новый пароль")
        for field in (self.current, self.new, self.repeat):
            field.setMinimumHeight(38)
            layout.addWidget(field)

        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet(f"color: {self.p['danger']}; font-size: 12px;")
        self.error.setVisible(False)
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        if ctx.email.startswith("guest@"):
            hint.setText("Для гостевого профиля пароль не задан — смена недоступна.")
            for field in (self.current, self.new, self.repeat):
                field.setEnabled(False)
            save.setEnabled(False)

    def _save(self) -> None:
        if self.new.text() != self.repeat.text():
            self.error.setText("Новые пароли не совпадают")
            self.error.setVisible(True)
            return
        try:
            self.ctx.auth.change_password(self.ctx.user_id, self.current.text(), self.new.text())
        except AuthError as exc:
            self.error.setText(str(exc))
            self.error.setVisible(True)
            return
        self.accept()


class SettingsPage(Page):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(ctx, parent)
        self.p = theme.CURRENT
        self.add_header("Настройки", "Поведение приложения и ваши данные")

        self._build_account()
        self._build_appearance()
        self._build_tracking()
        self._build_clipboard()
        self._build_system()
        self._build_remote()
        self._build_data()
        self._build_about()
        self.v.addStretch(1)

    # ------------------------------------------------------------- sections
    def _card(self, title: str, subtitle: str, icon_name: str) -> Card:
        card = Card(title, subtitle, icon_name)
        card.body.setContentsMargins(0, 4, 0, 0)
        self.v.addWidget(card)
        return card

    def _build_account(self) -> None:
        card = Card("Аккаунт", "", "user")
        row = QHBoxLayout()
        row.setSpacing(14)
        avatar = Avatar(self.ctx.user_initial or "?", 46)
        row.addWidget(avatar, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(3)
        email = self.ctx.email or "—"
        email_label = QLabel("Гость" if email.startswith("guest@") else email)
        email_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        info.addWidget(email_label)
        subtitle = QLabel("локальный профиль · вход по почте без сервера")
        subtitle.setObjectName("Subtitle")
        info.addWidget(subtitle)
        meta = QLabel(f"{APP_TITLE} {APP_VERSION} · данные в {data_dir()}")
        meta.setObjectName("Faint")
        meta.setWordWrap(True)
        info.addWidget(meta)
        row.addLayout(info, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        change = QPushButton("Сменить пароль")
        change.setCursor(Qt.PointingHandCursor)
        change.clicked.connect(self._change_password)
        logout = QPushButton("Выйти")
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self._logout)
        buttons.addWidget(change)
        buttons.addWidget(logout)
        row.addLayout(buttons)
        card.body.addLayout(row)
        self.v.addWidget(card)
        self.account_card = card

    def _build_appearance(self) -> None:
        card = self._card("Внешний вид", "", "sparkle")
        self.theme_switch = SegmentedControl([("dark", "Тёмная"), ("light", "Светлая")], self.ctx.settings.get("theme", "dark"))
        self.theme_switch.changed.connect(self._on_theme)
        card.body.addWidget(SettingsRow("Тема оформления", "Интерфейс перезагрузится без потери данных", self.theme_switch))

    def _build_tracking(self) -> None:
        card = self._card("Трекинг активности", "как собирается статистика приложений", "chart")
        self.interval_switch = SegmentedControl(
            [("2", "2 с"), ("5", "5 с"), ("10", "10 с"), ("30", "30 с")],
            str(self.ctx.settings.get("sample_seconds", 5)),
        )
        self.interval_switch.changed.connect(self._on_interval)
        card.body.addWidget(
            SettingsRow("Частота опроса активного окна", "реже — экономит ресурсы, реже — точнее график", self.interval_switch)
        )
        card.body.addWidget(hline())

        self.idle_switch = SegmentedControl(
            [("60", "1 мин"), ("120", "2 мин"), ("300", "5 мин"), ("600", "10 мин")],
            str(self.ctx.settings.get("idle_seconds", 120)),
        )
        self.idle_switch.changed.connect(self._on_idle)
        card.body.addWidget(
            SettingsRow("Не учитывать простой", "если нет ввода дольше указанного времени, оно не пишется в статистику", self.idle_switch)
        )
        card.body.addWidget(hline())

        excluded_host = QWidget()
        excluded_layout = QVBoxLayout(excluded_host)
        excluded_layout.setContentsMargins(0, 4, 0, 0)
        excluded_layout.setSpacing(6)
        label = QLabel("Исключённые приложения")
        label.setStyleSheet("font-size: 12.5px; font-weight: 600;")
        excluded_layout.addWidget(label)
        hint = QLabel("Через запятую, например: steam.exe, telegram.exe. FIDEXE и системные окна исключены всегда.")
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        excluded_layout.addWidget(hint)
        self.excluded_field = QLineEdit(str(self.ctx.settings.get("excluded_apps", "")))
        self.excluded_field.setPlaceholderText("app.exe, other.exe")
        self.excluded_field.editingFinished.connect(self._save_excluded)
        excluded_layout.addWidget(self.excluded_field)
        card.body.addWidget(excluded_host)

    def _build_clipboard(self) -> None:
        card = self._card("Буфер обмена", "", "clipboard")
        self.limit_switch = SegmentedControl(
            [("100", "100"), ("500", "500"), ("1000", "1000"), ("0", "∞")],
            str(self.ctx.settings.get("history_limit", 500)),
        )
        self.limit_switch.changed.connect(self._on_limit)
        card.body.addWidget(
            SettingsRow("Сколько записей хранить", "старые записи удаляются автоматически (закреплённые остаются)", self.limit_switch)
        )
        card.body.addWidget(hline())

        self.images_toggle = ToggleSwitch(bool(self.ctx.settings.get("capture_images", True)))
        self.images_toggle.toggled.connect(self._on_images)
        card.body.addWidget(
            SettingsRow("Сохранять картинки", "скриншоты и изображения занимают место на диске", self.images_toggle)
        )
        card.body.addWidget(hline())

        self.notify_toggle = ToggleSwitch(bool(self.ctx.settings.get("notify_on_copy", False)))
        self.notify_toggle.toggled.connect(lambda v: self._set("notify_on_copy", v))
        card.body.addWidget(
            SettingsRow("Уведомлять при копировании", "всплывающее уведомление в трее", self.notify_toggle)
        )

    def _build_system(self) -> None:
        card = self._card("Система", "", "monitor")
        self.autostart_toggle = ToggleSwitch(bool(self.ctx.settings.get("autostart", False)))
        self.autostart_toggle.toggled.connect(self._on_autostart)
        row = SettingsRow("Запускать вместе с Windows", "добавляет FIDEXE в автозагрузку пользователя", self.autostart_toggle)
        card.body.addWidget(row)
        if not autostart.is_supported():
            self.autostart_toggle.setEnabled(False)
            row.subtitle.setText("Доступно только в Windows")
        card.body.addWidget(hline())

        self.tray_toggle = ToggleSwitch(bool(self.ctx.settings.get("close_to_tray", True)))
        self.tray_toggle.toggled.connect(lambda v: self._set("close_to_tray", v))
        card.body.addWidget(
            SettingsRow("Сворачивать в трей при закрытии", "крестик скрывает окно, приложение продолжает считать", self.tray_toggle)
        )
        card.body.addWidget(hline())

        self.minimized_toggle = ToggleSwitch(bool(self.ctx.settings.get("start_minimized", False)))
        self.minimized_toggle.toggled.connect(lambda v: self._set("start_minimized", v))
        card.body.addWidget(
            SettingsRow("Стартовать свёрнутым", "окно не открывается при автозапуске", self.minimized_toggle)
        )

    def _build_remote(self) -> None:
        card = self._card("Телефон и блокировка", "управление этим компьютером по Wi-Fi", "lock")
        self.remote_toggle = ToggleSwitch(self.ctx.remote_enabled)
        self.remote_toggle.toggled.connect(self._on_remote_toggle)
        card.body.addWidget(
            SettingsRow(
                "Разрешить управление с телефона",
                "приложение FIDEXE Remote на Android сможет блокировать этот ПК в той же Wi-Fi сети",
                self.remote_toggle,
            )
        )
        card.body.addWidget(hline())

        self.remote_host = QLabel("Не подключено")
        self.remote_host.setWordWrap(True)
        self.remote_host.setObjectName("Subtitle")
        card.body.addWidget(self.remote_host)

        address_row = QHBoxLayout()
        address_row.setSpacing(8)
        self.remote_address = QLabel("—")
        self.remote_address.setObjectName("Mono")
        self.remote_address.setTextInteractionFlags(Qt.TextSelectableByMouse)
        address_row.addWidget(self.remote_address)
        self.copy_address = QPushButton("Скопировать адрес")
        self.copy_address.setCursor(Qt.PointingHandCursor)
        self.copy_address.clicked.connect(self._copy_address)
        address_row.addWidget(self.copy_address)
        self.lock_test = QPushButton("Заблокировать сейчас")
        self.lock_test.setCursor(Qt.PointingHandCursor)
        self.lock_test.clicked.connect(self._lock_now)
        address_row.addWidget(self.lock_test)
        address_row.addStretch(1)
        card.body.addLayout(address_row)

        self.remote_hint = QLabel("")
        self.remote_hint.setObjectName("Faint")
        self.remote_hint.setWordWrap(True)
        card.body.addWidget(self.remote_hint)

        self._remote_timer = QTimer(self)
        self._remote_timer.setInterval(5000)
        self._remote_timer.timeout.connect(self._refresh_remote)
        self._remote_timer.start()
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        running = self.ctx.remote.running
        self.copy_address.setEnabled(running)
        if running:
            self.remote_address.setText(self.ctx.remote.address)
            self.remote_host.setText(
                f"Компьютер: {remote.hostname()} · подключённых телефонов: {self.ctx.remote.session_count()}"
            )
        else:
            self.remote_address.setText("—")
            self.remote_host.setText("Сервер выключен")
        if not power.lock_supported():
            self.remote_hint.setText("Блокировка работает только в Windows.")
            self.lock_test.setEnabled(False)
        elif not [e for e in self.ctx.store.emails() if not e.startswith("guest@")]:
            self.remote_hint.setText(
                "Сначала войдите по почте (не гостем) — телефон авторизуется той же почтой и паролем, "
                "что и на ноутбуке."
            )
        else:
            self.remote_hint.setText(
                "Телефон и ноутбук должны быть в одной Wi-Fi сети. Пароль не передаётся: телефон "
                "доказывает знание пароля HMAC-подписью, сервер работает только в локальной сети."
            )

    def _on_remote_toggle(self, enabled: bool) -> None:
        ok = self.ctx.set_remote_enabled(enabled)
        if enabled and not ok:
            self.remote_toggle.setChecked(False)
            self.ctx.toast.emit("Не удалось открыть порт 47811 — возможно, он занят", "error")
        elif enabled:
            self.ctx.toast.emit("Управление с телефона включено", "ok")
        else:
            self.ctx.toast.emit("Управление с телефона выключено", "ok")
        self._refresh_remote()

    def _copy_address(self) -> None:
        if not self.ctx.remote.running:
            return
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(self.ctx.remote.address)
        self.ctx.toast.emit("Адрес скопирован", "ok")

    def _lock_now(self) -> None:
        if not power.lock_supported():
            self.ctx.toast.emit("Блокировка доступна только в Windows", "warn")
            return
        self.ctx.toast.emit("Блокирую компьютер…", "warn")
        QTimer.singleShot(400, power.lock_workstation)

    def _build_data(self) -> None:
        card = self._card("Данные", "", "shield")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        open_folder = QPushButton("Открыть папку данных")
        open_folder.setCursor(Qt.PointingHandCursor)
        open_folder.clicked.connect(self._open_folder)

        export_json_button = QPushButton("Экспорт JSON")
        export_json_button.setCursor(Qt.PointingHandCursor)
        export_json_button.clicked.connect(self._export_json)

        export_csv_button = QPushButton("Экспорт статистики CSV")
        export_csv_button.setCursor(Qt.PointingHandCursor)
        export_csv_button.clicked.connect(self._export_csv)

        wipe = QPushButton("Удалить все данные")
        wipe.setObjectName("Danger")
        wipe.setCursor(Qt.PointingHandCursor)
        wipe.clicked.connect(self._wipe)
        for button in (open_folder, export_json_button, export_csv_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(wipe)
        card.body.addLayout(buttons)

    def _build_about(self) -> None:
        card = self._card("О программе", "", "info")
        text = QLabel(
            f"{APP_TITLE} {APP_VERSION} — лёгкий трекер активности и истории буфера обмена для Windows.\n"
            "Работает полностью офлайн: ни один байт не отправляется в интернет. "
            "Аккаунт нужен только для разделения профилей на одном компьютере."
        )
        text.setWordWrap(True)
        text.setObjectName("Subtitle")
        card.body.addWidget(text)
        shortcuts = QLabel("Горячие клавиши: Ctrl+1…4 — разделы, Ctrl+F — поиск по буферу, Ctrl+Shift+P — пауза трекинга.")
        shortcuts.setObjectName("Faint")
        shortcuts.setWordWrap(True)
        card.body.addWidget(shortcuts)

    # -------------------------------------------------------------- actions
    def _set(self, key: str, value) -> None:
        self.ctx.settings.set(key, value)

    def _on_theme(self, name: str) -> None:
        self.ctx.set_theme(name)

    def _on_interval(self, value: str) -> None:
        self.ctx.settings.set("sample_seconds", int(value))
        self.ctx.tracker.apply_interval()

    def _on_idle(self, value: str) -> None:
        self.ctx.settings.set("idle_seconds", int(value))

    def _on_limit(self, value: str) -> None:
        limit = int(value)
        self.ctx.settings.set("history_limit", limit)
        self.ctx.store.prune_clips(self.ctx.user_id, limit)
        self.ctx.toast.emit("Лимит истории обновлён", "ok")

    def _on_images(self, enabled: bool) -> None:
        self.ctx.settings.set("capture_images", enabled)
        self.ctx.refresh_clipboard_settings()

    def _on_autostart(self, enabled: bool) -> None:
        if not autostart.is_supported():
            return
        ok = autostart.set_enabled(enabled)
        if ok:
            self.ctx.settings.set("autostart", enabled)
            self.ctx.toast.emit("Автозапуск включён" if enabled else "Автозапуск отключён", "ok")
        else:
            self.autostart_toggle.setChecked(not enabled)
            self.ctx.toast.emit("Не удалось изменить автозапуск", "error")

    def _save_excluded(self) -> None:
        self.ctx.settings.set("excluded_apps", self.excluded_field.text().strip())
        self.ctx.toast.emit("Список исключений сохранён", "ok")

    def _change_password(self) -> None:
        dialog = ChangePasswordDialog(self.ctx, self)
        if dialog.exec() == QDialog.Accepted:
            self.ctx.toast.emit("Пароль обновлён", "ok")

    def _logout(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Выход")
        box.setText("Выйти из аккаунта?")
        box.setInformativeText("Трекинг остановится, данные останутся на диске.")
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.button(QMessageBox.Yes).setText("Выйти")
        box.button(QMessageBox.Cancel).setText("Отмена")
        if box.exec() == QMessageBox.Yes:
            self.ctx.sign_out()

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    def _export_json(self) -> None:
        default = f"fidexe_export_{datetime.now():%Y%m%d_%H%M}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт данных", default, "JSON (*.json)")
        if not path:
            return
        try:
            count = export_json(self.ctx.store, self.ctx.user_id, Path(path), self.ctx.email)
            self.ctx.toast.emit(f"Экспортировано записей: {count}", "ok")
        except OSError as exc:
            self.ctx.toast.emit(f"Ошибка экспорта: {exc}", "error")

    def _export_csv(self) -> None:
        default = f"fidexe_usage_{datetime.now():%Y%m%d_%H%M}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт статистики", default, "CSV (*.csv)")
        if not path:
            return
        try:
            count = export_usage_csv(self.ctx.store, self.ctx.user_id, Path(path), days=30)
            self.ctx.toast.emit(f"Экспортировано строк: {count}", "ok")
        except OSError as exc:
            self.ctx.toast.emit(f"Ошибка экспорта: {exc}", "error")

    def _wipe(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Удаление данных")
        box.setText("Удалить всю историю буфера обмена и статистику?")
        box.setInformativeText("Аккаунт останется, но данные восстановить не получится.")
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.button(QMessageBox.Yes).setText("Удалить всё")
        box.button(QMessageBox.Cancel).setText("Отмена")
        if box.exec() != QMessageBox.Yes:
            return
        self.ctx.store.clear_clips(self.ctx.user_id, keep_pinned=False)
        self.ctx.store.delete_user_data(self.ctx.user_id)
        self.ctx.toast.emit("Все данные удалены", "ok")
