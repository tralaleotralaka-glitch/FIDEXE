"""Sign in / sign up window shown before the main dashboard."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..core.auth import AuthError
from ..core.paths import APP_TAGLINE, APP_TITLE, APP_VERSION
from . import icons, theme
from .widgets import SegmentedControl, ToggleSwitch


class StrengthBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.score = 0
        self.setFixedHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_score(self, score: int) -> None:
        self.score = max(0, min(4, score))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = [self.p["danger"], self.p["warn"], self.p["warn"], self.p["mint"], self.p["mint"]]
        labels = ["", "слабый", "средний", "хороший", "надёжный"]
        slot = self.width() / 4.0
        for i in range(4):
            rect = QRectF(i * slot + 2, 3, slot - 4, 5)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.p["card_hover"]))
            painter.drawRoundedRect(rect, 2.5, 2.5)
            if i < self.score:
                painter.setBrush(QColor(colors[self.score]))
                painter.drawRoundedRect(rect, 2.5, 2.5)
        painter.setFont(self._font())
        painter.setPen(QColor(self.p["muted"]))
        painter.drawText(QRectF(0, 8, self.width(), 12), Qt.AlignRight, labels[self.score])

    def _font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(10)
        return font


def password_score(password: str) -> int:
    if not password:
        return 0
    score = 0
    if len(password) >= 6:
        score += 1
    if len(password) >= 10:
        score += 1
    if any(c.isdigit() for c in password) and any(c.isalpha() for c in password):
        score += 1
    if any(not c.isalnum() for c in password):
        score += 1
    return min(4, score)


class BrandPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.p = theme.CURRENT
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 36, 30, 32)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(icons.pixmap("sparkle", "#FFFFFF", 26))
        logo.setFixedSize(46, 46)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background: rgba(255,255,255,0.18); border-radius: 14px;")
        layout.addWidget(logo)

        title = QLabel(APP_TITLE)
        title.setStyleSheet("color: #FFFFFF; font-size: 27px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(title)

        tagline = QLabel(APP_TAGLINE + " — всё под контролем\nна одном экране.")
        tagline.setStyleSheet("color: rgba(255,255,255,0.82); font-size: 13px; line-height: 19px;")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)
        layout.addSpacing(18)

        features = [
            ("clipboard", "История буфера обмена", "текст, ссылки, код и картинки"),
            ("chart", "Статистика приложений", "графики по дням и часам"),
            ("shield", "Данные только локально", "всё хранится на этом ПК"),
        ]
        for icon_name, head, sub in features:
            row = QHBoxLayout()
            row.setSpacing(11)
            badge = QLabel()
            badge.setPixmap(icons.pixmap(icon_name, "#FFFFFF", 16))
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background: rgba(255,255,255,0.16); border-radius: 9px;")
            row.addWidget(badge, 0, Qt.AlignTop)
            block = QVBoxLayout()
            block.setSpacing(0)
            head_label = QLabel(head)
            head_label.setStyleSheet("color: #FFFFFF; font-size: 12.5px; font-weight: 600;")
            sub_label = QLabel(sub)
            sub_label.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 11px;")
            block.addWidget(head_label)
            block.addWidget(sub_label)
            row.addLayout(block, 1)
            layout.addLayout(row)
            layout.addSpacing(6)

        layout.addStretch(1)
        version = QLabel(f"Версия {APP_VERSION} · Windows 10/11")
        version.setStyleSheet("color: rgba(255,255,255,0.55); font-size: 11px;")
        layout.addWidget(version)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#6B5BF6"))
        gradient.setColorAt(0.55, QColor("#4A47C9"))
        gradient.setColorAt(1.0, QColor("#16213E"))
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        painter.fillPath(path, gradient)

        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 18))
        painter.drawEllipse(QRectF(rect.width() - 150, -70, 260, 260))
        painter.setBrush(QColor(46, 230, 168, 34))
        painter.drawEllipse(QRectF(-90, rect.height() - 190, 250, 250))
        painter.restore()

        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 18, 18)


class LoginWindow(QWidget):
    logged_in = Signal(int, bool)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.p = theme.CURRENT
        self.setObjectName("Root")
        self.setWindowTitle(f"{APP_TITLE} — вход")
        self.setWindowIcon(icons.icon("sparkle", "#7B6CFF", 64))
        self.setFixedSize(900, 560)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(BrandPanel())

        form_host = QWidget()
        form_host.setStyleSheet(f"background: {self.p['bg']};")
        host_layout = QVBoxLayout(form_host)
        host_layout.setContentsMargins(54, 40, 54, 40)
        root.addWidget(form_host, 1)

        self.form = QVBoxLayout()
        self.form.setSpacing(10)
        host_layout.addLayout(self.form)
        host_layout.addStretch(1)

        heading = QLabel("С возвращением")
        heading.setObjectName("Title")
        self.form.addWidget(heading)

        self.subheading = QLabel("Войдите, чтобы увидеть свою статистику и буфер обмена")
        self.subheading.setObjectName("Subtitle")
        self.subheading.setWordWrap(True)
        self.form.addWidget(self.subheading)
        self.form.addSpacing(8)

        self.mode = SegmentedControl([("login", "Вход"), ("register", "Регистрация")], "login")
        self.mode.changed.connect(self._on_mode)
        self.form.addWidget(self.mode)
        self.form.addSpacing(6)

        self.email = QLineEdit()
        self.email.setPlaceholderText("you@mail.ru")
        self.email.setMinimumHeight(42)
        self.email.addAction(icons.icon("mail", self.p["muted"], 16), QLineEdit.LeadingPosition)
        self.form.addWidget(self._labelled("Почта", self.email))

        self.password = QLineEdit()
        self.password.setPlaceholderText("Введите пароль")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(42)
        self.password.addAction(icons.icon("lock", self.p["muted"], 16), QLineEdit.LeadingPosition)
        self._eye = self.password.addAction(
            icons.icon("eye", self.p["muted"], 16), QLineEdit.TrailingPosition
        )
        self._eye.setToolTip("Показать пароль")
        self._eye.triggered.connect(self._toggle_echo)
        self.form.addWidget(self._labelled("Пароль", self.password))

        self.strength = StrengthBar()
        self.strength.setVisible(False)
        self.form.addWidget(self.strength)

        self.remember_row = QWidget()
        remember_layout = QHBoxLayout(self.remember_row)
        remember_layout.setContentsMargins(0, 4, 0, 4)
        keep = QLabel("Запомнить меня на этом компьютере")
        keep.setObjectName("Subtitle")
        self.remember = ToggleSwitch(True)
        remember_layout.addWidget(keep)
        remember_layout.addStretch(1)
        remember_layout.addWidget(self.remember)
        self.form.addWidget(self.remember_row)

        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet(
            f"color: {self.p['danger']}; background: {self.p['danger_soft']};"
            "border-radius: 8px; padding: 8px 10px; font-size: 12px;"
        )
        self.error.setVisible(False)
        self.form.addWidget(self.error)

        self.submit = QPushButton("Войти")
        self.submit.setObjectName("Primary")
        self.submit.setMinimumHeight(44)
        self.submit.setCursor(Qt.PointingHandCursor)
        self.submit.clicked.connect(self._submit)
        self.form.addWidget(self.submit)

        guest_row = QHBoxLayout()
        guest_row.setSpacing(6)
        guest_hint = QLabel("Нет аккаунта?")
        guest_hint.setObjectName("Subtitle")
        self.guest = QPushButton("Продолжить без почты")
        self.guest.setObjectName("Link")
        self.guest.setCursor(Qt.PointingHandCursor)
        self.guest.clicked.connect(self._guest)
        guest_row.addStretch(1)
        guest_row.addWidget(guest_hint)
        guest_row.addWidget(self.guest)
        guest_row.addStretch(1)
        self.form.addLayout(guest_row)

        self.form.addSpacing(4)
        privacy = QLabel(
            "Аккаунт локальный: почта используется как логин, письма не отправляются, "
            "пароль хранится в виде хеша PBKDF2-SHA256."
        )
        privacy.setObjectName("Faint")
        privacy.setWordWrap(True)
        self.form.addWidget(privacy)

        for field in (self.email, self.password):
            field.returnPressed.connect(self._submit)
        self.password.textChanged.connect(self._update_strength)

        if ctx.store.emails():
            self.email.setFocus()
        else:
            self._on_mode("register")

    # ---------------------------------------------------------------- helpers
    def _labelled(self, text: str, widget: QWidget) -> QWidget:
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(text)
        label.setObjectName("Subtitle")
        layout.addWidget(label)
        layout.addWidget(widget)
        return holder

    def _toggle_echo(self) -> None:
        hidden = self.password.echoMode() == QLineEdit.Password
        self.password.setEchoMode(QLineEdit.Normal if hidden else QLineEdit.Password)
        self._eye.setIcon(icons.icon("eye-off" if hidden else "eye", self.p["muted"], 16))

    def _update_strength(self, text: str) -> None:
        if self.mode.current != "register":
            self.strength.setVisible(False)
            return
        self.strength.setVisible(True)
        self.strength.set_score(password_score(text))

    def _on_mode(self, mode: str) -> None:
        if self.mode.current != mode:
            self.mode.set_current(mode)
        register = mode == "register"
        self.mode.set_current(mode)
        self.subheading.setText(
            "Создайте аккаунт: данные будут привязаны к вашей почте"
            if register
            else "Войдите, чтобы увидеть свою статистику и буфер обмена"
        )
        self.submit.setText("Создать аккаунт" if register else "Войти")
        self.remember_row.setVisible(not register)
        self.strength.setVisible(register and bool(self.password.text()))
        self.strength.set_score(password_score(self.password.text()))
        self._hide_error()

    def _show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.setVisible(True)

    def _hide_error(self) -> None:
        self.error.setVisible(False)

    def _busy(self, busy: bool) -> None:
        self.submit.setEnabled(not busy)
        self.submit.setText("Подождите…" if busy else ("Создать аккаунт" if self.mode.current == "register" else "Войти"))

    # ---------------------------------------------------------------- actions
    def _submit(self) -> None:
        self._hide_error()
        email = self.email.text().strip()
        password = self.password.text()
        self._busy(True)
        try:
            if self.mode.current == "register":
                user_id = self.ctx.auth.register(email, password)
                remember = True
            else:
                user_id = self.ctx.auth.login(email, password)
                remember = self.remember.isChecked()
        except AuthError as exc:
            self._busy(False)
            self._show_error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - surface unexpected issues instead of crashing
            self._busy(False)
            self._show_error(f"Что-то пошло не так: {exc}")
            return
        self._busy(False)
        if self.mode.current == "register":
            self.ctx.toast.emit("Аккаунт создан. Добро пожаловать!", "ok")
        self.logged_in.emit(user_id, remember)

    def _guest(self) -> None:
        user_id = self.ctx.auth.guest_user()
        self.ctx.toast.emit("Вы вошли как гость — данные хранятся локально", "ok")
        self.logged_in.emit(user_id, True)
