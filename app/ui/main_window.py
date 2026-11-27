"""Main window: sidebar navigation, page stack, tray integration and toasts."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..core.paths import APP_TITLE, APP_VERSION, resource_path
from . import icons, theme
from .pages.clipboard_page import ClipboardPage
from .pages.dashboard import DashboardPage
from .pages.settings_page import SettingsPage
from .pages.stats_page import StatsPage
from .widgets import Avatar, IconButton, SidebarButton

NAV = [
    ("dashboard", "Обзор", "grid"),
    ("clipboard", "Буфер обмена", "clipboard"),
    ("stats", "Статистика", "chart"),
    ("settings", "Настройки", "settings"),
]

KIND_STYLE = {
    "ok": ("check", "mint", "mint_soft"),
    "warn": ("info", "warn", "warn_soft"),
    "error": ("info", "danger", "danger_soft"),
}


class Toast(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setVisible(False)
        self._label = QLabel(self)
        self._label.setStyleSheet("font-size: 12.5px; font-weight: 600;")
        self._icon = QLabel(self)
        self._icon.setFixedSize(20, 20)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 16, 10)
        layout.setSpacing(9)
        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def show_message(self, message: str, kind: str = "ok", msec: int = 2600) -> None:
        icon_name, color_key, soft_key = KIND_STYLE.get(kind, KIND_STYLE["ok"])
        self._icon.setPixmap(icons.pixmap(icon_name, self.p[color_key], 15))
        self._label.setText(message)
        self.setStyleSheet(
            f"background: {self.p['card']}; border: 1px solid {self.p[color_key]}; border-radius: 12px;"
        )
        self._label.setStyleSheet(f"color: {self.p['text']}; font-size: 12.5px; font-weight: 600;")
        self.adjustSize()
        self._reposition()
        self._effect.setOpacity(0.0)
        self.setVisible(True)
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._hide_timer.start(msec)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 26
        self.move(max(12, x), max(12, y))

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._on_faded)
        self._anim.start()

    def _on_faded(self) -> None:
        try:
            self._anim.finished.disconnect(self._on_faded)
        except (RuntimeError, TypeError):
            pass
        self.setVisible(False)


def build_tray_icon() -> QIcon:
    path = resource_path("assets/app.png")
    if path.exists():
        return QIcon(str(path))
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#7B6CFF"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    font = QFont()
    font.setPixelSize(30)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(pix.rect(), Qt.AlignCenter, "F")
    painter.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.p = theme.CURRENT
        self.setWindowTitle(f"{APP_TITLE} — {self._display_name()}")
        self.setWindowIcon(build_tray_icon())
        self.setMinimumSize(1040, 700)
        self.resize(1260, 820)
        self._closing_to_tray = False
        self._tray_hint_shown = False
        self.tray = None

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.pages = {
            "dashboard": DashboardPage(ctx),
            "clipboard": ClipboardPage(ctx),
            "stats": StatsPage(ctx),
            "settings": SettingsPage(ctx),
        }
        for key, _label, _icon in NAV:
            self.stack.addWidget(self.pages[key])
        layout.addWidget(self.stack, 1)

        self.toast = Toast(root)
        self._build_shortcuts()
        self._build_tray()

        ctx.toast.connect(self._on_toast)
        ctx.watcher.captured.connect(self._on_captured)
        ctx.status_changed.connect(self._on_status_changed)
        self._select("dashboard")
        self.pages["dashboard"].refresh()

        self._session_timer = QTimer(self)
        self._session_timer.setInterval(15_000)
        self._session_timer.timeout.connect(self._update_session_time)
        self._session_timer.start()
        self._update_session_time()

    # -------------------------------------------------------------- sidebar
    def _display_name(self) -> str:
        email = self.ctx.email
        return "Гость" if email.startswith("guest@") else email

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(238)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(9)
        logo = QLabel()
        logo.setFixedSize(32, 32)
        logo.setPixmap(icons.pixmap("sparkle", "#FFFFFF", 17))
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"background: {self.p['accent']}; border-radius: 10px;")
        brand.addWidget(logo)
        title = QLabel(APP_TITLE)
        title.setStyleSheet("font-size: 16px; font-weight: 800; letter-spacing: 1.5px;")
        brand.addWidget(title)
        brand.addStretch(1)
        self.menu_button = IconButton("chevron-down", "Меню приложения", self.p["muted"], 16)
        self.menu_button.clicked.connect(self._show_menu)
        brand.addWidget(self.menu_button)
        layout.addLayout(brand)
        layout.addSpacing(18)

        self.nav_buttons: dict[str, SidebarButton] = {}
        for key, label, icon_name in NAV:
            button = SidebarButton(key, label, icon_name)
            button.clicked.connect(lambda checked=False, k=key: self._select(k))
            self.nav_buttons[key] = button
            layout.addWidget(button)
        layout.addSpacing(12)

        # tracking mini card
        status_box = QWidget()
        status_box.setObjectName("InnerCard")
        box_layout = QVBoxLayout(status_box)
        box_layout.setContentsMargins(12, 10, 12, 10)
        box_layout.setSpacing(6)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        box_layout.addWidget(self.status_label)
        self.session_label = QLabel("0 мин сегодня")
        self.session_label.setObjectName("Faint")
        box_layout.addWidget(self.session_label)
        self.pause_button = QPushButton("Пауза")
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.clicked.connect(self._toggle_pause)
        box_layout.addWidget(self.pause_button)
        layout.addWidget(status_box)

        layout.addStretch(1)

        # user chip
        user_box = QWidget()
        user_layout = QHBoxLayout(user_box)
        user_layout.setContentsMargins(4, 0, 0, 0)
        user_layout.setSpacing(8)
        self.avatar = Avatar(self.ctx.user_initial or "?", 34)
        user_layout.addWidget(self.avatar)
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self.user_email = QLabel(self._display_name())
        self.user_email.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        self.user_email.setMaximumWidth(120)
        text_box.addWidget(self.user_email)
        role = QLabel("локальный аккаунт")
        role.setObjectName("Faint")
        text_box.addWidget(role)
        user_layout.addLayout(text_box, 1)
        logout = QPushButton()
        logout.setObjectName("IconButton")
        logout.setIcon(icons.icon("logout", self.p["muted"], 16))
        logout.setIconSize(QSize(16, 16))
        logout.setFixedSize(30, 30)
        logout.setCursor(Qt.PointingHandCursor)
        logout.setToolTip("Выйти из аккаунта")
        logout.clicked.connect(self._logout)
        user_layout.addWidget(logout)
        layout.addWidget(user_box)

        hint = QLabel("Сворачивается в трей · Ctrl+1…4")
        hint.setObjectName("Faint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self._sync_status()
        return sidebar

    # ------------------------------------------------------------- app menu
    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        for idx, (key, label, _icon) in enumerate(NAV, start=1):
            action = QAction(f"{label}\tCtrl+{idx}", menu)
            action.triggered.connect(lambda checked=False, k=key: self._select(k))
            menu.addAction(action)
        menu.addSeparator()

        self.menu_pause = QAction("Пауза трекинга", menu)
        self.menu_pause.triggered.connect(self._toggle_pause)
        menu.addAction(self.menu_pause)

        if self.ctx.remote_needs_firewall:
            firewall_action = QAction("Разрешить доступ с телефона (брандмауэр)…", menu)
            firewall_action.triggered.connect(self.ctx.fix_firewall)
            menu.addAction(firewall_action)
            menu.addSeparator()

        theme_menu = menu.addMenu("Тема оформления")
        group = QActionGroup(theme_menu)
        for key, label in (("dark", "Тёмная"), ("light", "Светлая")):
            action = QAction(label, theme_menu, checkable=True)
            action.setChecked(self.ctx.settings.get("theme", "dark") == key)
            action.triggered.connect(lambda checked=False, k=key: self.ctx.set_theme(k))
            group.addAction(action)
            theme_menu.addAction(action)
        menu.addSeparator()

        export_action = QAction("Экспорт данных (JSON)…", menu)
        export_action.triggered.connect(self._export_json)
        menu.addAction(export_action)

        folder_action = QAction("Открыть папку данных", menu)
        folder_action.triggered.connect(self._open_data_folder)
        menu.addAction(folder_action)
        menu.addSeparator()

        about_action = QAction(f"О FIDEXE {APP_VERSION}", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        return menu

    def _show_menu(self) -> None:
        if not hasattr(self, "_menu"):
            self._menu = self._build_menu()
        self._sync_status()
        self._menu.popup(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def _export_json(self) -> None:
        from datetime import datetime
        from pathlib import Path

        from ..core.exporter import export_json

        default = f"fidexe_export_{datetime.now():%Y%m%d_%H%M}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт данных", default, "JSON (*.json)")
        if not path:
            return
        try:
            count = export_json(self.ctx.store, self.ctx.user_id, Path(path), self.ctx.email)
            self._on_toast(f"Экспортировано записей: {count}", "ok")
        except OSError as exc:
            self._on_toast(f"Ошибка экспорта: {exc}", "error")

    def _open_data_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from ..core.paths import data_dir

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    def _show_about(self) -> None:
        from ..core.paths import APP_TAGLINE, data_dir

        box = QMessageBox(self)
        box.setWindowTitle(f"О {APP_TITLE}")
        box.setTextFormat(Qt.RichText)
        box.setText(
            f"<b>{APP_TITLE} {APP_VERSION}</b><br>{APP_TAGLINE}<br><br>"
            "Полностью офлайн: история буфера и статистика хранятся только на этом компьютере."
        )
        box.setInformativeText(
            f"Папка данных: {data_dir()}\n\n"
            "Горячие клавиши: Ctrl+1…4 — разделы, Ctrl+F — поиск по буферу, "
            "Ctrl+Shift+P — пауза трекинга, Esc — свернуть в трей."
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    # ---------------------------------------------------------------- tray
    def _build_tray(self) -> None:
        self.tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(build_tray_icon(), self)
        tray.setToolTip(f"{APP_TITLE} — {self._display_name()}")
        menu = QMenu()
        show_action = QAction("Открыть FIDEXE", self)
        show_action.triggered.connect(self.show_window)
        self.tray_pause = QAction("Пауза трекинга", self)
        self.tray_pause.triggered.connect(self._toggle_pause)
        clipboard_action = QAction("Буфер обмена", self)
        clipboard_action.triggered.connect(lambda: (self.show_window(), self._select("clipboard")))
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(clipboard_action)
        menu.addSeparator()
        menu.addAction(self.tray_pause)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self.tray = tray

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.show_window()

    # ------------------------------------------------------------ shortcuts
    def _build_shortcuts(self) -> None:
        from PySide6.QtGui import QKeySequence, QShortcut

        for idx, (key, _label, _icon) in enumerate(NAV, start=1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{idx}"), self)
            shortcut.activated.connect(lambda k=key: self._select(k))
        search = QShortcut(QKeySequence("Ctrl+F"), self)
        search.activated.connect(self._focus_search)
        pause = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        pause.activated.connect(self._toggle_pause)

    def _focus_search(self) -> None:
        self._select("clipboard")
        self.pages["clipboard"].search.setFocus()

    # ---------------------------------------------------------------- pages
    def _select(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        for name, button in self.nav_buttons.items():
            button.setChecked(name == key)
            button.update()
        self.stack.setCurrentWidget(page)
        page.on_show()

    # --------------------------------------------------------------- status
    def _sync_status(self) -> None:
        paused = bool(self.ctx.settings.get("tracking_paused", False))
        color = self.p["warn"] if paused else self.p["mint"]
        dot = "●"
        text = "Трекинг на паузе" if paused else "Трекинг активен"
        self.status_label.setText(f"<span style='color:{color}'>{dot}</span> {text}")
        self.pause_button.setText("Продолжить" if paused else "Поставить на паузу")
        self.pause_button.setObjectName("Primary" if paused else "")
        self.pause_button.style().unpolish(self.pause_button)
        self.pause_button.style().polish(self.pause_button)
        if self.tray is not None:
            self.tray_pause.setText("Продолжить трекинг" if paused else "Пауза трекинга")
        if hasattr(self, "_menu"):
            self.menu_pause.setText("Продолжить трекинг" if paused else "Пауза трекинга")

    def _toggle_pause(self) -> None:
        paused = not bool(self.ctx.settings.get("tracking_paused", False))
        self.ctx.set_tracking_paused(paused)
        self._sync_status()
        self.pages["dashboard"]._sync_pause_button()
        self._on_toast("Трекинг приостановлен" if paused else "Трекинг снова включён", "warn" if paused else "ok")

    def _update_session_time(self) -> None:
        if not self.ctx.user_id:
            return
        from datetime import date, datetime

        start = int(datetime.combine(date.today(), datetime.min.time()).timestamp())
        seconds = self.ctx.store.total_seconds(self.ctx.user_id, start, int(datetime.now().timestamp()))
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        text = f"{hours} ч {minutes:02d} мин сегодня" if hours else f"{minutes} мин сегодня"
        self.session_label.setText(text)

    # --------------------------------------------------------------- events
    def _on_toast(self, message: str, kind: str = "ok") -> None:
        self.toast.show_message(message, kind)
        if kind == "error" and hasattr(self, "pages"):
            pass

    def _on_status_changed(self, active: bool = True) -> None:
        self._sync_status()
        if hasattr(self, "pages"):
            self.pages["dashboard"]._sync_pause_button()

    def _on_captured(self, kind: str, text: str, path: str) -> None:
        if self.ctx.settings.get("notify_on_copy", False) and self.tray is not None:
            preview = "Изображение" if kind == "image" else (text.strip().replace("\n", " ")[:60] or "запись")
            self.tray.showMessage("Скопировано в FIDEXE", preview, QSystemTrayIcon.Information, 1800)
        if self.ctx.user_id:
            self._update_session_time()

    def show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _logout(self) -> None:
        self.ctx.sign_out()

    def _quit(self) -> None:
        self._closing_to_tray = False
        QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        close_to_tray = bool(self.ctx.settings.get("close_to_tray", True))
        if close_to_tray and self.tray is not None and not self._closing_to_tray:
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage(
                    f"{APP_TITLE} работает в трее",
                    "Трекинг продолжается. Двойной клик по иконке вернёт окно.",
                    QSystemTrayIcon.Information,
                    3000,
                )
            return
        if self.tray is not None:
            self.tray.hide()
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast._reposition()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape and self.ctx.settings.get("close_to_tray", True) and self.tray:
            self.hide()
            return
        super().keyPressEvent(event)
