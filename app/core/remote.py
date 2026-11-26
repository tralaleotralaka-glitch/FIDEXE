"""Local-network remote control: lets the Android app lock this computer.

Protocol (JSON over HTTP on the LAN, no internet involved):

    GET  /api/info                      -> app metadata + masked account hint
    POST /api/pair            {code}     -> {token, ...}   (6-digit code from the desktop)
    POST /api/auth/challenge  {email}    -> {salt, iterations, challenge}
    POST /api/auth/proof      {email, challenge, proof} -> {token, expires_in}
    GET  /api/status          (Bearer)   -> live statistics of the desktop
    POST /api/command         (Bearer)   -> {cmd: lock|sleep|pause|resume}

Two ways in:

* pairing code -- the desktop shows six digits that rotate every minute
  (HMAC-SHA256 of a per-installation secret and the current minute). Typing them
  on the phone opens the control panel straight away;
* account -- the phone derives the same PBKDF2 hash the desktop stored
  (salt/iterations are public) and proves knowledge of the password by signing a
  random challenge with HMAC-SHA256, so the password never crosses the network.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from PySide6.QtCore import QObject, Signal

from . import power
from .db import Storage
from .paths import APP_NAME, APP_VERSION, data_dir

log = logging.getLogger(__name__)

SERVICE_TYPE = "_fidexe._tcp.local."
DEFAULT_PORT = 47811
PROTOCOL = 1
TOKEN_TTL = 2 * 3600
CHALLENGE_TTL = 120
PAIR_CODE_PERIOD = 60          # seconds a pairing code stays valid
PAIR_CODE_DIGITS = 6
PAIR_SECRET_FILE = "pair_secret"
AUTH_WINDOW = 300
AUTH_MAX_FAILURES = 8
MAX_BODY = 64 * 1024
ALLOWED_COMMANDS = {"lock", "sleep", "pause", "resume"}


def local_ip() -> str:
    """Best-effort LAN address of this machine."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def hostname() -> str:
    try:
        return socket.gethostname().split(".")[0]
    except OSError:
        return "DESKTOP"


def pair_code_for(secret: bytes, window: int) -> str:
    """Six digits derived from the installation secret and the current minute."""
    digest = hmac.new(secret, f"fidexe-pair:{window}".encode("utf-8"), hashlib.sha256).digest()
    value = int.from_bytes(digest[:8], "big") % (10 ** PAIR_CODE_DIGITS)
    return f"{value:0{PAIR_CODE_DIGITS}d}"


def format_pair_code(code: str) -> str:
    """`123456` -> `123 456` for display."""
    return f"{code[:3]} {code[3:]}" if len(code) == PAIR_CODE_DIGITS else code


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    shown = name[:1] if len(name) <= 2 else name[:2]
    return f"{shown}***@{domain}"


@dataclass(slots=True)
class Session:
    user_id: int
    email: str
    device: str
    created: float
    expires: float


class RemoteError(Exception):
    """Authentication / request failure with a user facing message."""


class RemoteControl(QObject):
    """Threaded LAN server; all UI notifications go through Qt signals."""

    locked = Signal(str)                  # device name
    command_done = Signal(str, str)       # command, device
    client_authenticated = Signal(str, str)  # email, device
    started = Signal(str, int)            # address, port
    stopped = Signal()
    failed_attempt = Signal(str)          # client address

    def __init__(
        self,
        store: Storage,
        status_provider: Callable[[int], dict],
        account_provider: Callable[[], int] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.status_provider = status_provider
        self.account_provider = account_provider
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._zeroconf = None
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}
        self._challenges: dict[str, tuple[int, float]] = {}
        self._failures: dict[str, list[float]] = {}
        self._port = DEFAULT_PORT
        self._pair_secret: bytes | None = None
        self.action_override: Callable[[str], bool] | None = None

    # ------------------------------------------------------------------ state
    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def port(self) -> int:
        return self._port

    @property
    def address(self) -> str:
        return f"{local_ip()}:{self._port}"

    def session_count(self) -> int:
        now = time.time()
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.expires > now)

    # ------------------------------------------------------------- lifecycle
    def start(self, port: int = DEFAULT_PORT) -> bool:
        with self._lock:
            if self._server is not None:
                return True
            self._port = int(port or DEFAULT_PORT)
            try:
                server = ThreadingHTTPServer(("0.0.0.0", self._port), _RequestHandler)
            except OSError as exc:
                log.error("Не удалось запустить LAN-сервер на порту %s: %s", self._port, exc)
                return False
            server.daemon_threads = True
            server.remote = self  # type: ignore[attr-defined]
            self._server = server
            self._thread = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.4}, daemon=True, name="fidexe-remote"
            )
            self._thread.start()
        self._register_mdns()
        log.info("LAN-сервер запущен на %s", self.address)
        self.started.emit(local_ip(), self._port)
        return True

    def stop(self) -> None:
        self._unregister_mdns()
        with self._lock:
            server = self._server
            self._server = None
            self._sessions.clear()
            self._challenges.clear()
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:  # noqa: BLE001
                log.exception("Ошибка остановки LAN-сервера")
            log.info("LAN-сервер остановлен")
            self.stopped.emit()

    # ------------------------------------------------------------------- mDNS
    def _register_mdns(self) -> None:
        try:
            from zeroconf import ServiceInfo, Zeroconf
        except Exception:  # noqa: BLE001 - optional dependency
            log.info("zeroconf недоступен: автопоиск с телефона не будет работать")
            return
        try:
            zc = Zeroconf()
            name = f"FIDEXE-{hostname()}.{SERVICE_TYPE}"
            info = ServiceInfo(
                SERVICE_TYPE,
                name,
                addresses=[socket.inet_aton(local_ip())],
                port=self._port,
                properties={
                    "version": APP_VERSION,
                    "host": hostname(),
                    "protocol": str(PROTOCOL),
                },
                server=f"{hostname().lower()}.local.",
            )
            zc.register_service(info)
            self._zeroconf = zc
            log.info("mDNS: опубликован сервис %s", name)
        except Exception:  # noqa: BLE001
            log.exception("Не удалось опубликовать mDNS-сервис")
            self._zeroconf = None

    def _unregister_mdns(self) -> None:
        zc = self._zeroconf
        self._zeroconf = None
        if zc is None:
            return
        try:
            zc.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------- pairing code
    def pair_secret(self) -> bytes:
        """Per-installation secret for the rotating code, created on first use."""
        with self._lock:
            if self._pair_secret is not None:
                return self._pair_secret
            path = data_dir() / PAIR_SECRET_FILE
            secret = b""
            try:
                if path.exists():
                    stored = path.read_text(encoding="ascii").strip()
                    if len(stored) >= 32:
                        secret = bytes.fromhex(stored)
            except (OSError, ValueError):
                secret = b""
            if not secret:
                secret = secrets.token_bytes(32)
                try:
                    path.write_text(secret.hex(), encoding="ascii")
                    try:
                        os.chmod(path, 0o600)
                    except OSError:
                        pass
                except OSError:
                    log.warning("Не удалось сохранить секрет кода подключения")
            self._pair_secret = secret
            return secret

    def pair_window(self, now: float | None = None) -> int:
        return int((time.time() if now is None else now) // PAIR_CODE_PERIOD)

    def pair_code(self) -> str:
        """Current six digits shown in the desktop settings."""
        return pair_code_for(self.pair_secret(), self.pair_window())

    def pair_remaining(self) -> int:
        """Seconds until the displayed code rotates (1..60)."""
        return PAIR_CODE_PERIOD - int(time.time()) % PAIR_CODE_PERIOD

    def _account_row(self):
        user_id = int(self.account_provider() if self.account_provider else 0)
        row = self.store.user_by_id(user_id) if user_id else None
        if row is not None and not str(row["email"]).startswith("guest@"):
            return row
        for email in self.store.emails():
            if email.startswith("guest@"):
                continue
            fallback = self.store.find_user(email)
            if fallback is not None:
                return fallback
        return None

    def pair(self, code: str, device: str, client: str) -> dict:
        """Authenticate a phone with the rotating code shown on this computer."""
        if self._rate_limited(client):
            raise RemoteError("Слишком много попыток входа. Подождите несколько минут")
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if len(digits) != PAIR_CODE_DIGITS:
            self._note_failure(client)
            raise RemoteError(f"Код состоит из {PAIR_CODE_DIGITS} цифр — посмотрите его в настройках FIDEXE")
        row = self._account_row()
        if row is None:
            raise RemoteError("На ноутбуке никто не вошёл в аккаунт — войдите по почте в FIDEXE")
        secret = self.pair_secret()
        window = self.pair_window()
        # the previous minute is accepted too, so a code does not die mid-typing
        accepted = any(
            hmac.compare_digest(pair_code_for(secret, w), digits) for w in (window, window - 1)
        )
        if not accepted:
            self._note_failure(client)
            raise RemoteError("Неверный код — обновите его в настройках FIDEXE на ноутбуке")
        self._clear_failures(client)
        log.info("Телефон подключён по коду: %s", (device or "Android")[:60])
        return self._start_session(row, device)

    # ------------------------------------------------------------------- auth
    def _rate_limited(self, client: str) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._failures.get(client, []) if now - t < AUTH_WINDOW]
            self._failures[client] = hits
            return len(hits) >= AUTH_MAX_FAILURES

    def _note_failure(self, client: str) -> None:
        with self._lock:
            self._failures.setdefault(client, []).append(time.time())
        self.failed_attempt.emit(client)

    def _clear_failures(self, client: str) -> None:
        with self._lock:
            self._failures.pop(client, None)

    def challenge(self, email: str) -> dict:
        row = self.store.find_user(email)
        if row is None:
            raise RemoteError("Аккаунт с такой почтой не найден на этом компьютере")
        challenge = secrets.token_hex(24)
        with self._lock:
            self._challenges[challenge] = (int(row["id"]), time.time() + CHALLENGE_TTL)
        return {
            "salt": row["salt"],
            "iterations": 240_000,
            "challenge": challenge,
            "expires_in": CHALLENGE_TTL,
        }

    def verify_proof(self, email: str, challenge: str, proof: str, device: str, client: str) -> dict:
        if self._rate_limited(client):
            raise RemoteError("Слишком много попыток входа. Подождите несколько минут")
        row = self.store.find_user(email)
        if row is None:
            self._note_failure(client)
            raise RemoteError("Аккаунт не найден")
        with self._lock:
            entry = self._challenges.pop(challenge, None)
        if entry is None or entry[1] < time.time() or entry[0] != int(row["id"]):
            self._note_failure(client)
            raise RemoteError("Код подтверждения устарел, попробуйте снова")
        expected = hmac.new(
            bytes.fromhex(row["pw_hash"]), challenge.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, (proof or "").strip().lower()):
            self._note_failure(client)
            raise RemoteError("Неверный пароль")
        self._clear_failures(client)
        log.info("Телефон подключён: %s (%s)", (device or "Android")[:60], mask_email(row["email"]))
        return self._start_session(row, device)

    def _start_session(self, row, device: str) -> dict:
        token = secrets.token_urlsafe(32)
        now = time.time()
        session = Session(
            user_id=int(row["id"]),
            email=row["email"],
            device=(device or "Android")[:60],
            created=now,
            expires=now + TOKEN_TTL,
        )
        with self._lock:
            self._sessions[token] = session
        self.client_authenticated.emit(session.email, session.device)
        return {
            "token": token,
            "expires_in": TOKEN_TTL,
            "account": session.email,
            "host": hostname(),
        }

    def session_for(self, token: str) -> Session:
        now = time.time()
        with self._lock:
            stale = [t for t, s in self._sessions.items() if s.expires < now]
            for key in stale:
                self._sessions.pop(key, None)
            session = self._sessions.get(token)
        if session is None:
            raise RemoteError("Сессия истекла, войдите заново")
        return session

    # --------------------------------------------------------------- commands
    def run_command(self, cmd: str, device: str) -> bool:
        if cmd not in ALLOWED_COMMANDS:
            raise RemoteError("Неизвестная команда")
        if self.action_override is not None:
            ok = bool(self.action_override(cmd))
        elif cmd == "lock":
            ok = power.lock_workstation()
        elif cmd == "sleep":
            ok = power.sleep_workstation()
        else:
            ok = True  # pause / resume are applied by the GUI layer
        if cmd == "lock":
            self.locked.emit(device)
        self.command_done.emit(cmd, device)
        log.info("Команда с телефона: %s -> %s (%s)", cmd, ok, device)
        return ok

    def info(self) -> dict:
        with self._lock:
            accounts = sorted({s.email for s in self._sessions.values()})
        del accounts
        emails = [mask_email(e) for e in self.store.emails() if not e.startswith("guest@")]
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "protocol": PROTOCOL,
            "host": hostname(),
            "address": f"{local_ip()}:{self._port}",
            "accounts": emails,
            "requires_account": not emails,
            "pairing": True,
            "pair_code_ttl": PAIR_CODE_PERIOD,
        }

    def status(self, user_id: int) -> dict:
        data = self.status_provider(user_id)
        data["host"] = hostname()
        data["locked_supported"] = power.lock_supported()
        return data


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = f"FIDEXE/{APP_VERSION}"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------- plumbing
    @property
    def remote(self) -> "RemoteControl":
        return self.server.remote  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _client(self) -> str:
        return self.client_address[0] if self.client_address else "?"

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise RemoteError("Слишком большой запрос")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise RemoteError("Некорректный JSON") from None
        if not isinstance(data, dict):
            raise RemoteError("Ожидался JSON-объект")
        return data

    def _token(self) -> str:
        header = self.headers.get("Authorization") or ""
        if not header.lower().startswith("bearer "):
            raise RemoteError("Требуется авторизация")
        return header[7:].strip()

    def _session(self) -> Session:
        return self.remote.session_for(self._token())

    # ---------------------------------------------------------------- routes
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path == "/api/ping":
                self._send(200, {"ok": True, "app": APP_NAME, "version": APP_VERSION})
            elif path == "/api/info":
                self._send(200, self.remote.info())
            elif path == "/api/status":
                session = self._session()
                self._send(200, self.remote.status(session.user_id))
            else:
                self._send(404, {"error": "Не найдено"})
        except RemoteError as exc:
            self._send(401, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path == "/api/pair":
                data = self._body()
                self._send(
                    200,
                    self.remote.pair(
                        str(data.get("code", "")),
                        str(data.get("device", "Android")),
                        self._client(),
                    ),
                )
                return
            if path == "/api/auth/challenge":
                data = self._body()
                self._send(200, self.remote.challenge(str(data.get("email", ""))))
                return
            if path == "/api/auth/proof":
                data = self._body()
                self._send(
                    200,
                    self.remote.verify_proof(
                        str(data.get("email", "")),
                        str(data.get("challenge", "")),
                        str(data.get("proof", "")),
                        str(data.get("device", "Android")),
                        self._client(),
                    ),
                )
                return
            if path == "/api/command":
                session = self._session()
                data = self._body()
                cmd = str(data.get("cmd", ""))
                ok = self.remote.run_command(cmd, session.device)
                self._send(200, {"ok": ok, "cmd": cmd})
                return
            self._send(404, {"error": "Не найдено"})
        except RemoteError as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - never leak a traceback to clients
            log.exception("Ошибка обработки запроса %s", path)
            self._send(500, {"error": f"Внутренняя ошибка: {exc}"})
