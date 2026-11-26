"""Standalone mock of the FIDEXE desktop LAN API.

Used by the Android UI test: the emulator talks to this server exactly like it
talks to the real desktop app, so the whole auth + lock flow is exercised.

    python3 tools/mock_remote.py --port 47811
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import zlib
import hmac
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EMAIL = "demo@fidexe.app"
PASSWORD = "demo-pass-123"
SALT = "00112233445566778899aabbccddeeff"
ITERATIONS = 240_000
PW_HASH = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), bytes.fromhex(SALT), ITERATIONS).hex()
TOKEN = "demo-token-1234567890"
PAIR_SECRET = secrets.token_bytes(32)
PAIR_PERIOD = 60


def pair_code_for(window: int) -> str:
    """Same derivation as the desktop app: six digits per minute."""
    digest = hmac.new(PAIR_SECRET, f"fidexe-pair:{window}".encode(), hashlib.sha256).digest()
    return f"{int.from_bytes(digest[:8], 'big') % 1_000_000:06d}"


def current_pair_code() -> str:
    return pair_code_for(int(time.time() // PAIR_PERIOD))
CHALLENGES: dict[str, float] = {}
STATE = {"locked": 0, "commands": [], "paused": False, "closed": []}

APPS = [
    {"pid": 101, "app": "chrome.exe", "title": "GitHub — FIDEXE (mock)", "active": True},
    {"pid": 202, "app": "code.exe", "title": "MainActivity.java — Visual Studio Code", "active": False},
    {"pid": 303, "app": "telegram.exe", "title": "Telegram", "active": False},
    {"pid": 404, "app": "explorer.exe", "title": "Загрузки", "active": False},
]


def make_frame(frame: int, width: int = 640, height: int = 360) -> bytes:
    """Tiny synthetic "webcam" frame so the phone has a real JPEG/PNG to render."""
    rows = bytearray()
    bar = (frame * 24) % width
    for y in range(height):
        rows.append(0)  # PNG filter: none
        for x in range(width):
            r = int(20 + 30 * y / height)
            g = int(28 + 24 * x / width)
            b = int(46 + 40 * y / height)
            if abs(x - bar) < 40:
                r, g, b = min(255, r + 90), min(255, g + 70), min(255, b + 120)
            if (x // 80 + y // 80) % 2 == 0:
                r, g, b = min(255, r + 8), min(255, g + 8), min(255, b + 10)
            rows += bytes((r, g, b))
    return png(width, height, bytes(rows))


def png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


FRAMES = {"count": 0}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[mock]", fmt % args, flush=True)

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except ValueError:
            return {}

    def _authorised(self) -> bool:
        header = self.headers.get("Authorization") or ""
        if not header.startswith("Bearer "):
            self._send(401, {"error": "Требуется авторизация"})
            return False
        if header[7:] != TOKEN:
            self._send(401, {"error": "Сессия истекла, войдите заново"})
            return False
        return True

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/api/ping":
            self._send(200, {"ok": True, "app": "FIDEXE", "version": "2.0.0"})
        elif path == "/api/info":
            self._send(200, {
                "app": "FIDEXE", "version": "2.0.0", "protocol": 1,
                "host": "DESKTOP-DEMO", "address": "127.0.0.1:47811",
                "accounts": ["de***@fidexe.app"], "requires_account": False,
                "pairing": True, "pair_code_ttl": PAIR_PERIOD,
            })
        elif path == "/api/status":
            if not self._authorised():
                return
            self._send(200, {
                "host": "DESKTOP-DEMO",
                "today_seconds": 15840,
                "current_app": "chrome.exe",
                "current_title": "GitHub — FIDEXE (mock)",
                "top_apps": [
                    {"app": "chrome.exe", "seconds": 5400},
                    {"app": "code.exe", "seconds": 3600},
                    {"app": "telegram.exe", "seconds": 1200},
                ],
                "clip_count": 42,
                "paused": STATE["paused"],
                "tracking": not STATE["paused"],
                "locked_supported": True,
            })
        elif path == "/api/apps":
            if not self._authorised():
                return
            self._send(200, {
                "apps": [a for a in APPS if a["pid"] not in [c["pid"] for c in STATE["closed"]]],
                "supported": True,
                "host": "DESKTOP-DEMO",
            })
        elif path == "/api/camera/info":
            if not self._authorised():
                return
            self._send(200, {
                "supported": True, "allowed": True, "active": True,
                "width": 640, "height": 360, "fps": 8, "error": "",
            })
        elif path == "/api/camera/frame":
            if not self._authorised():
                return
            FRAMES["count"] += 1
            body = make_frame(FRAMES["count"])
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/demo/code":
            # mock-only helper so the UI test can type the real current code
            self._send(200, {
                "code": current_pair_code(),
                "left": PAIR_PERIOD - int(time.time()) % PAIR_PERIOD,
            })
        elif path == "/api/state":
            self._send(200, {
                "locked": STATE["locked"],
                "commands": STATE["commands"],
                "closed": STATE["closed"],
                "camera_frames": FRAMES["count"],
            })
        else:
            self._send(404, {"error": "Не найдено"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        data = self._body()
        if path == "/api/pair":
            digits = "".join(ch for ch in str(data.get("code", "")) if ch.isdigit())
            window = int(time.time() // PAIR_PERIOD)
            accepted = any(pair_code_for(w) == digits for w in (window, window - 1))
            if len(digits) != 6:
                self._send(400, {"error": "Код состоит из 6 цифр"})
                return
            if not accepted:
                print("[mock] WRONG PAIR CODE:", digits, flush=True)
                self._send(400, {"error": "Неверный код — обновите его на ноутбуке"})
                return
            print("[mock] phone paired with code:", data.get("device"), flush=True)
            self._send(200, {
                "token": TOKEN, "expires_in": 7200, "account": EMAIL,
                "host": "DESKTOP-DEMO",
            })
            return
        if path == "/api/auth/challenge":
            if str(data.get("email", "")).lower() != EMAIL:
                self._send(400, {"error": "Аккаунт с такой почтой не найден на этом компьютере"})
                return
            challenge = secrets.token_hex(24)
            CHALLENGES[challenge] = time.time() + 120
            self._send(200, {
                "salt": SALT, "iterations": ITERATIONS,
                "challenge": challenge, "expires_in": 120,
            })
            return
        if path == "/api/auth/proof":
            challenge = str(data.get("challenge", ""))
            if challenge not in CHALLENGES or CHALLENGES.pop(challenge) < time.time():
                self._send(400, {"error": "Код подтверждения устарел, попробуйте снова"})
                return
            expected = hmac.new(bytes.fromhex(PW_HASH), challenge.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, str(data.get("proof", "")).lower()):
                self._send(400, {"error": "Неверный пароль"})
                return
            print("[mock] phone authenticated:", data.get("device"), flush=True)
            self._send(200, {"token": TOKEN, "expires_in": 7200, "account": EMAIL})
            return
        if path == "/api/apps/close":
            if not self._authorised():
                return
            pid = int(data.get("pid", 0))
            name = next((a["app"] for a in APPS if a["pid"] == pid), "?")
            if not any(a["pid"] == pid for a in APPS):
                self._send(400, {"error": "Приложение не закрылось — возможно, оно уже закрыто"})
                return
            print("[mock] CLOSE APP:", name, pid, flush=True)
            STATE["closed"].append({"pid": pid, "app": name})
            STATE["commands"].append("close_app")
            self._send(200, {"ok": True, "pid": pid})
            return
        if path == "/api/command":
            if not self._authorised():
                return
            cmd = str(data.get("cmd", ""))
            STATE["commands"].append(cmd)
            if cmd == "lock":
                STATE["locked"] += 1
                print("[mock] LOCK COMMAND RECEIVED", flush=True)
            if cmd == "pause":
                STATE["paused"] = True
            if cmd == "resume":
                STATE["paused"] = False
            self._send(200, {"ok": True, "cmd": cmd})
            return
        self._send(404, {"error": "Не найдено"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=47811)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.daemon_threads = True
    print(
        f"[mock] FIDEXE desktop API on 0.0.0.0:{args.port} "
        f"(demo@fidexe.app / demo-pass-123, code {current_pair_code()})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
