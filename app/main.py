"""Application bootstrap: single instance, theme, login flow and tray."""
from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtCore import QObject, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from .context import AppContext
from .core.paths import APP_NAME, APP_TITLE, APP_VERSION, data_dir
from .ui import theme
from .ui.login import LoginWindow
from .ui.main_window import MainWindow, build_tray_icon

SERVER_NAME = "FIDEXE-single-instance"
PAGE_ORDER = ("dashboard", "clipboard", "stats", "settings")


def setup_logging() -> None:
    log_file = data_dir() / "fidexe.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )

    def excepthook(exc_type, exc_value, exc_tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("Необработанная ошибка:\n%s", text)
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle(f"{APP_TITLE} — ошибка")
            box.setText("Что-то пошло не так, но данные не потеряны.")
            box.setInformativeText(str(exc_value)[:400])
            box.setDetailedText(text)
            box.exec()
        except Exception:
            pass

    sys.excepthook = excepthook


class AppController(QObject):
    """Owns windows and reacts to session/theme changes."""

    def __init__(self, app: QApplication, ctx: AppContext, *, start_minimized: bool = False) -> None:
        super().__init__()
        self.app = app
        self.ctx = ctx
        self.window: MainWindow | None = None
        self.login: LoginWindow | None = None
        self._start_minimized = start_minimized
        self._server: QLocalServer | None = None

        ctx.session_changed.connect(self._on_session)
        ctx.theme_changed.connect(self._on_theme)
        ctx.toast.connect(self._on_toast)
        self._listen()

        remembered = int(ctx.settings.get("session_user", 0) or 0)
        if remembered and ctx.store.user_by_id(remembered):
            ctx.sign_in(remembered, True)
        else:
            self.show_login()

    # ---------------------------------------------------------- single instance
    def _listen(self) -> None:
        QLocalServer.removeServer(SERVER_NAME)
        server = QLocalServer(self)
        if server.listen(SERVER_NAME):
            server.newConnection.connect(self._on_new_connection)
            self._server = server

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda: self._bring_to_front())
        socket.disconnected.connect(socket.deleteLater)
        self._bring_to_front()

    def _bring_to_front(self) -> None:
        if self.window is not None:
            self.window.show_window()
        elif self.login is not None:
            self.login.showNormal()
            self.login.raise_()
            self.login.activateWindow()

    # ------------------------------------------------------------------ windows
    def show_login(self) -> None:
        if self.login is not None:
            self.login.show()
            return
        login = LoginWindow(self.ctx)
        login.logged_in.connect(self._on_logged_in)
        login.show()
        self.login = login

    def _on_logged_in(self, user_id: int, remember: bool) -> None:
        login = self.login
        self.login = None
        if login is not None:
            login.hide()
            login.deleteLater()
        self.ctx.sign_in(user_id, remember)

    def _on_session(self, user_id: int) -> None:
        if user_id:
            login = self.login
            if login is not None:
                self.login = None
                login.close()
                login.deleteLater()
            show = not (self._start_minimized and self._tray_available())
            self._start_minimized = False
            if self.window is None:
                self.window = MainWindow(self.ctx)
                if show:
                    self.window.show()
                    self.window.raise_()
            else:
                self.window.show_window()
        else:
            QTimer.singleShot(0, self._logout_flow)

    def _tray_available(self) -> bool:
        from PySide6.QtWidgets import QSystemTrayIcon

        return QSystemTrayIcon.isSystemTrayAvailable()

    def _logout_flow(self) -> None:
        window = self.window
        self.window = None
        self.show_login()
        if window is not None:
            window._closing_to_tray = False
            window.hide()
            window.deleteLater()

    def _on_theme(self, name: str) -> None:
        palette = theme.set_current(name)
        self.app.setStyleSheet(theme.build_stylesheet(palette))
        if self.window is not None:
            key = PAGE_ORDER[self.window.stack.currentIndex()]
            geometry = self.window.geometry()
            was_visible = self.window.isVisible()
            old = self.window
            self.window = None
            old._closing_to_tray = False
            old.hide()
            old.deleteLater()
            window = MainWindow(self.ctx)
            window.setGeometry(geometry)
            index = PAGE_ORDER.index(key) if key in PAGE_ORDER else 0
            window._select(PAGE_ORDER[index])
            self.window = window
            if was_visible:
                window.show()
        if self.login is not None:
            geometry = self.login.geometry()
            login = LoginWindow(self.ctx)
            login.setGeometry(geometry)
            login.logged_in.connect(self._on_logged_in)
            old_login = self.login
            self.login = login
            old_login.hide()
            old_login.deleteLater()
            login.show()

    def _on_toast(self, message: str, kind: str) -> None:
        if self.window is not None:
            self.window._on_toast(message, kind)

    # ------------------------------------------------------------------ shutdown
    def quit(self) -> None:
        if self._server is not None:
            self._server.close()
        self.ctx.shutdown()
        self.app.quit()


def run_selftest(app: QApplication) -> int:
    """Headless sanity check used by CI: boots the UI, walks every page, exits."""
    ctx = AppContext()
    theme.set_current(str(ctx.settings.get("theme", "dark")))
    app.setStyleSheet(theme.build_stylesheet(theme.CURRENT))
    ctx.sign_in(ctx.auth.guest_user(), True)
    window = MainWindow(ctx)
    window.resize(1200, 800)
    window.show()
    for key in PAGE_ORDER:
        window._select(key)
        for _ in range(2):
            app.processEvents()
        shot = data_dir() / f"selftest_{key}.png"
        window.grab().save(str(shot))
        print("page ok:", key, shot.stat().st_size if shot.exists() else 0)
    window.hide()
    window.deleteLater()
    ctx.shutdown()
    print("SELFTEST OK")
    return 0


def main() -> int:
    setup_logging()
    logging.info("Запуск %s %s", APP_TITLE, APP_VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setWindowIcon(build_tray_icon())

    if "--selftest" in sys.argv:
        return run_selftest(app)

    # Notify a running instance instead of starting a second copy.
    probe = QLocalSocket()
    probe.connectToServer(SERVER_NAME)
    if probe.waitForConnected(200):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(200)
        probe.disconnectFromServer()
        return 0
    probe.abort()

    ctx = AppContext()
    theme.set_current(str(ctx.settings.get("theme", "dark")))
    app.setStyleSheet(theme.build_stylesheet(theme.CURRENT))

    start_minimized = "--minimized" in sys.argv
    controller = AppController(app, ctx, start_minimized=start_minimized)
    app.aboutToQuit.connect(controller.quit)
    code = app.exec()
    controller.quit()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
