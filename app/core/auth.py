"""Local e-mail accounts with PBKDF2 password hashing."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from .db import Storage

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
ITERATIONS = 240_000


class AuthError(Exception):
    """Raised when registration / sign-in fails; message is user facing."""


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
    ).hex()


def validate_email(email: str) -> str:
    email = email.strip()
    if not EMAIL_RE.match(email):
        raise AuthError("Введите корректный адрес почты, например you@mail.ru")
    return email.lower()


def validate_password(password: str) -> str:
    if len(password) < 6:
        raise AuthError("Пароль должен содержать минимум 6 символов")
    if password.isdigit():
        raise AuthError("Пароль не должен состоять только из цифр")
    return password


class AuthService:
    def __init__(self, store: Storage) -> None:
        self.store = store

    def register(self, email: str, password: str) -> int:
        email = validate_email(email)
        validate_password(password)
        if self.store.find_user(email):
            raise AuthError("Аккаунт с такой почтой уже существует — войдите в него")
        salt = secrets.token_hex(16)
        return self.store.create_user(email, _hash(password, salt), salt)

    def login(self, email: str, password: str) -> int:
        email = email.strip().lower()
        if not email or not password:
            raise AuthError("Заполните почту и пароль")
        row = self.store.find_user(email)
        if row is None:
            raise AuthError("Аккаунт не найден. Проверьте почту или зарегистрируйтесь")
        candidate = _hash(password, row["salt"])
        if not hmac.compare_digest(candidate, row["pw_hash"]):
            raise AuthError("Неверный пароль")
        self.store.touch_login(int(row["id"]))
        return int(row["id"])

    def change_password(self, user_id: int, current: str, new: str) -> None:
        row = self.store.user_by_id(user_id)
        if row is None:
            raise AuthError("Аккаунт не найден")
        if not hmac.compare_digest(_hash(current, row["salt"]), row["pw_hash"]):
            raise AuthError("Текущий пароль неверен")
        validate_password(new)
        salt = secrets.token_hex(16)
        with self.store._lock:  # noqa: SLF001 - single-writer helper
            self.store._conn.execute(  # noqa: SLF001
                "UPDATE users SET pw_hash = ?, salt = ? WHERE id = ?",
                (_hash(new, salt), salt, user_id),
            )
            self.store._conn.commit()  # noqa: SLF001

    def guest_user(self) -> int:
        """A password-less local profile so the app is usable without signing up."""
        email = "guest@local"
        row = self.store.find_user(email)
        if row:
            self.store.touch_login(int(row["id"]))
            return int(row["id"])
        salt = secrets.token_hex(16)
        return self.store.create_user(email, _hash(secrets.token_hex(24), salt), salt)

    def email(self, user_id: int) -> str:
        row = self.store.user_by_id(user_id)
        return row["email"] if row else ""
